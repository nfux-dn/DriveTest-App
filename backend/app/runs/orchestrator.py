"""Run orchestration (spec sections 18-19, Phase 5).

Creates a run, an isolated workspace, fetches the exact Git revision (or uses
the local definitions source in dev), then executes each test sequentially in
its own process and stores independent results.

Execution runs in a background thread with its own DB session so the API request
returns immediately. ai_verdict/final_verdict are populated in later phases.
"""

from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select

from app.core.config import get_settings
from app.core.enums import ExecutionStatus, RunStatus
from app.db.session import SessionLocal
from app.environments.models import Environment
from app.git import service as git_service
from app.git.fetch import fetch_revision
from app.results.models import Artifact, TestRun
from app.runner.executor import ExecOutcome, execute_test
from app.runner.workspace import Workspace, create_workspace
from app.runs.models import Run
from app.suites.models import Suite

logger = logging.getLogger("drivetest.runs.orchestrator")


def start_run_async(run_id: str) -> None:
    """Kick off execution in a background thread."""
    thread = threading.Thread(target=_execute_run, args=(run_id,), name=f"run-{run_id}", daemon=True)
    thread.start()


def _execute_run(run_id: str) -> None:
    settings = get_settings()
    db = SessionLocal()
    try:
        run = db.get(Run, run_id)
        if run is None:
            logger.warning("run_missing run_id=%s", run_id)
            return

        run.status = RunStatus.RUNNING.value
        run.started_at = datetime.now(timezone.utc)
        db.commit()

        suite = db.get(Suite, run.suite_id)
        env = db.get(Environment, run.environment_id)
        workspace = create_workspace(settings.workspaces_path, run_id)

        source_root = _resolve_source(db, run, workspace)

        context_base = {
            "run_id": run_id,
            "suite_id": run.suite_id,
            "environment": {
                "id": env.id if env else None,
                "platform": env.platform if env else None,
                "system_type": env.system_type if env else None,
                "software_version": env.software_version if env else None,
            },
        }

        test_runs = db.scalars(
            select(TestRun).where(TestRun.run_id == run_id).order_by(TestRun.order_index)
        ).all()

        for tr in test_runs:
            _run_one_test(db, run, suite, source_root, workspace, tr, context_base, settings)

        run.status = RunStatus.COMPLETED.value
        run.finished_at = datetime.now(timezone.utc)
        db.commit()
        logger.info("run_completed run_id=%s", run_id)
    except Exception:  # noqa: BLE001 - ensure run is marked failed, then re-log
        logger.exception("run_failed run_id=%s", run_id)
        db.rollback()
        run = db.get(Run, run_id)
        if run is not None:
            run.status = RunStatus.FAILED.value
            run.finished_at = datetime.now(timezone.utc)
            db.commit()
    finally:
        db.close()


def _resolve_source(db, run: Run, workspace: Workspace) -> Path:
    """Return the directory that contains suites/<id>/tests/... for execution."""
    settings = get_settings()
    if run.repository and run.branch:
        token = git_service.reveal_token(db, run.user_id)
        commit_sha = fetch_revision(
            repo_dir=workspace.repo,
            full_name=run.repository,
            branch=run.branch,
            token=token,
            commit=run.commit_sha,
        )
        run.commit_sha = commit_sha
        db.commit()
        return workspace.repo
    # Dev fallback: run tests straight from the local definitions source.
    logger.info("run_using_local_definitions run_id=%s", run.id)
    return settings.definitions_path


def _run_one_test(db, run, suite, source_root, workspace, tr: TestRun, context_base, settings) -> None:
    tr.execution_status = ExecutionStatus.RUNNING.value
    tr.started_at = datetime.now(timezone.utc)
    db.commit()

    test_dir = source_root / "suites" / run.suite_id / "tests" / tr.test_id
    context = {**context_base, "test_id": tr.test_id, "values": run and _run_values(db, run)}

    outcome: ExecOutcome = execute_test(
        test_dir=test_dir,
        test_id=tr.test_id,
        context=context,
        results_dir=workspace.results,
        timeout_seconds=settings.test_timeout_seconds,
        max_capture_bytes=settings.max_capture_bytes,
    )

    tr.execution_status = outcome.execution_status.value
    tr.test_verdict = outcome.test_verdict
    tr.result_json = outcome.result_json
    tr.finished_at = datetime.now(timezone.utc)
    db.commit()

    _persist_logs(db, workspace, tr, outcome)
    logger.info(
        "test_stored run_id=%s test_id=%s status=%s verdict=%s",
        run.id,
        tr.test_id,
        tr.execution_status,
        tr.test_verdict,
    )


def _run_values(db, run: Run) -> dict:
    from app.prerequisites.models import PrerequisiteInstance

    inst = db.scalar(select(PrerequisiteInstance).where(PrerequisiteInstance.run_id == run.id))
    return dict(inst.values_json) if inst and inst.values_json else {}


def _persist_logs(db, workspace: Workspace, tr: TestRun, outcome: ExecOutcome) -> None:
    stdout_path = workspace.logs / f"{tr.test_id}.stdout.txt"
    stderr_path = workspace.logs / f"{tr.test_id}.stderr.txt"
    stdout_path.write_text(outcome.stdout or "", encoding="utf-8")
    stderr_path.write_text(outcome.stderr or "", encoding="utf-8")

    for path, artifact_type in ((stdout_path, "stdout"), (stderr_path, "stderr")):
        db.add(
            Artifact(
                test_run_id=tr.id,
                artifact_type=artifact_type,
                path_or_object_key=str(path),
                size=path.stat().st_size,
            )
        )
    db.commit()
