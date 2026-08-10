"""Run orchestration (spec sections 18-19, Phase 5).

Creates a run, an isolated workspace, fetches the exact Git revision (or uses
the local definitions source in dev), then executes each test sequentially in
its own process and stores independent results.

Execution runs in a background thread with its own DB session so the API request
returns immediately. ai_verdict/final_verdict are populated in later phases.
"""

from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select

from app.ai.base import AiRequest
from app.ai.factory import get_evaluator_for_user
from app.ai.prompts import POLICY_VERSION, PROMPT_VERSION
from app.connections.broker import ConnectionBroker
from app.connections.devices import resolve_required_devices
from app.connections.manager import ConnectionError as DeviceConnectionError
from app.connections.manager import ConnectionManager
from app.connections.transport import get_transport
from app.core.config import get_settings
from app.core.enums import ExecutionStatus, RunStatus
from app.core.errors import ApiError
from app.db.session import SessionLocal
from app.secrets.store import SecretStore
from app.evaluation.verdict import final_verdict_for_test
from app.git import service as git_service
from app.git.fetch import fetch_revision
from app.prerequisites.service import resolve_for as resolve_prereq_template
from app.results.models import AiEvaluation, Artifact, TestRun
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
        workspace = create_workspace(settings.workspaces_path, run_id)

        source_root = _resolve_source(db, run, workspace)

        values = _run_values(db, run)
        context_base = {
            "run_id": run_id,
            "suite_id": run.suite_id,
            "environment": {},
        }

        test_runs = db.scalars(
            select(TestRun).where(TestRun.run_id == run_id).order_by(TestRun.order_index)
        ).all()

        # Establish Run-owned device sessions and start the connection broker
        # before any test runs; close them in cleanup (spec section 51).
        manager = ConnectionManager(
            transport=get_transport(),
            command_timeout=settings.ssh_command_timeout_seconds,
            reconnect_attempts=settings.ssh_reconnect_attempts,
            context={"run_id": run_id},
        )
        broker = ConnectionBroker(manager)
        try:
            # Device sessions are prerequisite-driven (spec section 51): each
            # prerequisite field with a device_role opens one session.
            specs = []
            try:
                template = resolve_prereq_template(db, run.suite_id)
                specs = resolve_required_devices(template, values)
            except ApiError:
                specs = []  # no prerequisite template -> no device sessions
            if specs:
                manager.establish(specs, secret_resolver=SecretStore(db).reveal)
            broker.start()
            broker_env = {
                "DRIVETEST_BROKER_URL": broker.base_url or "",
                "DRIVETEST_BROKER_TOKEN": broker.token,
                "PYTHONPATH": settings.sdk_dir,
            }

            for tr in test_runs:
                _run_one_test(
                    db, run, suite, source_root, workspace, tr, context_base, settings, broker_env, manager
                )

            run.status = RunStatus.COMPLETED.value
            run.finished_at = datetime.now(timezone.utc)
            db.commit()
            logger.info("run_completed run_id=%s", run_id)
        except DeviceConnectionError:
            logger.exception("run_connection_setup_failed run_id=%s", run_id)
            _mark_tests_infra_error(db, test_runs)
            run.status = RunStatus.FAILED.value
            run.finished_at = datetime.now(timezone.utc)
            db.commit()
        finally:
            broker.stop()
            manager.close_all()
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


def _run_one_test(
    db, run, suite, source_root, workspace, tr: TestRun, context_base, settings, broker_env, manager
) -> None:
    tr.execution_status = ExecutionStatus.RUNNING.value
    tr.started_at = datetime.now(timezone.utc)
    db.commit()

    test_dir = source_root / "suites" / run.suite_id / "tests" / tr.test_id
    context = {**context_base, "test_id": tr.test_id, "values": _run_values(db, run)}

    # Mark where this test's device session begins so we can save it as an artifact.
    session_start = manager.transcript_len()

    outcome: ExecOutcome = execute_test(
        test_dir=test_dir,
        test_id=tr.test_id,
        context=context,
        results_dir=workspace.results,
        timeout_seconds=settings.test_timeout_seconds,
        max_capture_bytes=settings.max_capture_bytes,
        extra_env=broker_env,
    )

    tr.execution_status = outcome.execution_status.value
    tr.test_verdict = outcome.test_verdict
    tr.result_json = outcome.result_json
    tr.finished_at = datetime.now(timezone.utc)
    db.commit()

    session_text = manager.transcript_since(session_start)
    _persist_logs(db, workspace, tr, outcome, session_text)

    # AI review runs for every successfully executed test (spec section 6). For
    # non-COMPLETED executions AI does not produce a product verdict (spec 8).
    if outcome.execution_status == ExecutionStatus.COMPLETED:
        _evaluate_with_ai(db, run, test_dir, tr, outcome, settings, session_text)

    logger.info(
        "test_stored run_id=%s test_id=%s status=%s test_verdict=%s ai_verdict=%s final=%s",
        run.id,
        tr.test_id,
        tr.execution_status,
        tr.test_verdict,
        tr.ai_verdict,
        tr.final_verdict,
    )


def _evaluate_with_ai(
    db, run, test_dir: Path, tr: TestRun, outcome: ExecOutcome, settings, session_text: str
) -> None:
    meta = _load_test_metadata(test_dir)
    result = outcome.result_json or {}
    limit = settings.ai_max_log_excerpt_bytes

    # The files the AI reviews against the expected results (spec section 21).
    files: dict[str, str] = {}
    if session_text:
        files["ssh_session"] = session_text[:limit]
    if outcome.stdout:
        files["stdout"] = outcome.stdout[:limit]
    if outcome.stderr:
        files["stderr"] = outcome.stderr[:limit]
    if outcome.result_json is not None:
        files["result.json"] = json.dumps(outcome.result_json, indent=2)[:limit]

    request = AiRequest(
        test_id=tr.test_id,
        test_name=meta.get("name"),
        description=meta.get("description"),
        expected_behavior=meta.get("expected_behavior"),
        evaluation_instructions=meta.get("evaluation_instructions"),
        test_verdict=tr.test_verdict,
        measurements=result.get("measurements", {}) or {},
        observations=result.get("observations", []) or [],
        evidence=result.get("evidence", []) or [],
        artifacts=result.get("artifacts", []) or [],
        files=files,
    )

    evaluator = get_evaluator_for_user(db, run.user_id, settings)
    try:
        ai_result = evaluator.evaluate(request)
    except Exception:  # noqa: BLE001 - a failed AI review must not crash the run
        logger.exception("ai_evaluation_failed run_id=%s test_id=%s", run.id, tr.test_id)
        return

    db.add(
        AiEvaluation(
            test_run_id=tr.id,
            model=evaluator.model,
            prompt_version=PROMPT_VERSION,
            policy_version=POLICY_VERSION,
            ai_verdict=ai_result.ai_verdict.value,
            confidence=ai_result.confidence,
            summary=ai_result.summary,
            analysis_json={
                "observations": ai_result.observations,
                "anomalies": ai_result.anomalies,
                "evidence": [e.model_dump() for e in ai_result.evidence],
                "likely_root_cause": ai_result.likely_root_cause,
                "recommended_next_step": ai_result.recommended_next_step,
            },
        )
    )

    tr.ai_verdict = ai_result.ai_verdict.value
    tr.ai_confidence = ai_result.confidence
    final = final_verdict_for_test(tr.execution_status, tr.test_verdict, tr.ai_verdict)
    tr.final_verdict = final.value if final else None
    db.commit()


def _load_test_metadata(test_dir: Path) -> dict:
    """Read optional evaluation.md (AI evaluation instructions, spec 21).

    The markdown content is passed to the AI reviewer as the evaluation
    instructions / expected behavior for the test.
    """
    evaluation_md = test_dir / "evaluation.md"
    if not evaluation_md.exists():
        return {}
    try:
        text = evaluation_md.read_text(encoding="utf-8").strip()
    except OSError:
        return {}
    return {"evaluation_instructions": text, "expected_behavior": text}


def _run_values(db, run: Run) -> dict:
    from app.prerequisites.models import PrerequisiteInstance

    inst = db.scalar(select(PrerequisiteInstance).where(PrerequisiteInstance.run_id == run.id))
    return dict(inst.values_json) if inst and inst.values_json else {}


def _mark_tests_infra_error(db, test_runs: list[TestRun]) -> None:
    """If connection setup fails, no test can run; record INFRA_ERROR (spec 8/51)."""
    now = datetime.now(timezone.utc)
    for tr in test_runs:
        if tr.execution_status in (ExecutionStatus.PENDING.value, ExecutionStatus.RUNNING.value):
            tr.execution_status = ExecutionStatus.INFRA_ERROR.value
            tr.finished_at = now
    db.commit()


def _persist_logs(db, workspace: Workspace, tr: TestRun, outcome: ExecOutcome, session_text: str) -> None:
    """Write all files gathered for this test and register them as artifacts."""
    stdout_path = workspace.logs / f"{tr.test_id}.stdout.txt"
    stderr_path = workspace.logs / f"{tr.test_id}.stderr.txt"
    session_path = workspace.logs / f"{tr.test_id}.session.txt"
    stdout_path.write_text(outcome.stdout or "", encoding="utf-8")
    stderr_path.write_text(outcome.stderr or "", encoding="utf-8")
    session_path.write_text(session_text or "(no device commands were issued)\n", encoding="utf-8")

    files: list[tuple[Path, str]] = [
        (session_path, "ssh_session"),
        (stdout_path, "stdout"),
        (stderr_path, "stderr"),
    ]

    # The result.json the test wrote (if any), gathered as an artifact too.
    result_path = workspace.results / f"{tr.test_id}.result.json"
    if result_path.exists():
        files.append((result_path, "result"))

    for path, artifact_type in files:
        db.add(
            Artifact(
                test_run_id=tr.id,
                artifact_type=artifact_type,
                path_or_object_key=str(path),
                size=path.stat().st_size,
            )
        )
    db.commit()
