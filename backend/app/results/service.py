"""Result read services for individual test runs and their artifacts."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.enums import ExecutionStatus, FinalVerdict
from app.core.errors import ApiError
from app.results.models import AiEvaluation, Artifact, TestRun
from app.results.schemas import AiEvaluationOut, ArtifactOut, RunReport, TestRunDetailOut
from app.runs.models import Run
from app.runs.schemas import TestRunOut


def get_test_run(db: Session, test_run_id: str) -> TestRunDetailOut:
    tr = db.get(TestRun, test_run_id)
    if tr is None:
        raise ApiError(code="TEST_RUN_NOT_FOUND", message="Test run not found.", status_code=404)
    detail = TestRunDetailOut.model_validate(tr)
    detail.ai = _latest_ai(db, test_run_id)
    return detail


def _latest_ai(db: Session, test_run_id: str) -> AiEvaluationOut | None:
    ev = db.scalar(
        select(AiEvaluation)
        .where(AiEvaluation.test_run_id == test_run_id)
        .order_by(AiEvaluation.created_at.desc())
    )
    if ev is None:
        return None
    return AiEvaluationOut(
        model=ev.model,
        prompt_version=ev.prompt_version,
        policy_version=ev.policy_version,
        ai_verdict=ev.ai_verdict,
        confidence=ev.confidence,
        summary=ev.summary,
        analysis=ev.analysis_json or {},
    )


def build_report(db: Session, run_id: str) -> RunReport:
    run = db.get(Run, run_id)
    if run is None:
        raise ApiError(code="RUN_NOT_FOUND", message="Run not found.", status_code=404)
    rows = db.scalars(
        select(TestRun).where(TestRun.run_id == run_id).order_by(TestRun.order_index)
    ).all()

    counts = {
        "passed": 0,
        "failed": 0,
        "review_required": 0,
        "script_error": 0,
        "infra_error": 0,
        "timeout": 0,
        "other": 0,
    }
    for t in rows:
        counts[_categorize(t.execution_status, t.final_verdict)] += 1

    return RunReport(
        run_id=run.id,
        suite_id=run.suite_id,
        user_id=run.user_id,
        status=run.status,
        repository=run.repository,
        branch=run.branch,
        commit_sha=run.commit_sha,
        started_at=run.started_at,
        finished_at=run.finished_at,
        total=len(rows),
        tests=[TestRunOut.model_validate(t) for t in rows],
        **counts,
    )


def _categorize(execution_status: str, final_verdict: str | None) -> str:
    """Bucket a test for the report (execution errors kept separate, spec 8)."""
    if execution_status == ExecutionStatus.SCRIPT_ERROR.value:
        return "script_error"
    if execution_status == ExecutionStatus.INFRA_ERROR.value:
        return "infra_error"
    if execution_status == ExecutionStatus.TIMEOUT.value:
        return "timeout"
    if execution_status != ExecutionStatus.COMPLETED.value:
        return "other"
    if final_verdict == FinalVerdict.PASSED.value:
        return "passed"
    if final_verdict == FinalVerdict.REVIEW_REQUIRED.value:
        return "review_required"
    if final_verdict == FinalVerdict.FAILED.value:
        return "failed"
    return "other"


def list_artifacts(db: Session, test_run_id: str) -> list[ArtifactOut]:
    if db.get(TestRun, test_run_id) is None:
        raise ApiError(code="TEST_RUN_NOT_FOUND", message="Test run not found.", status_code=404)
    rows = db.scalars(select(Artifact).where(Artifact.test_run_id == test_run_id)).all()
    # Hide empty files (e.g. stdout/stderr with no output) from the listing.
    return [ArtifactOut.model_validate(a) for a in rows if (a.size or 0) > 0]


def _safe_artifact_path(path_or_key: str) -> Path:
    """Resolve an artifact path and ensure it is inside the workspaces dir (spec 37.7)."""
    workspaces = get_settings().workspaces_path.resolve()
    path = Path(path_or_key).resolve()
    try:
        path.relative_to(workspaces)
    except ValueError:
        raise ApiError(code="ARTIFACT_FORBIDDEN", message="Artifact path is not allowed.", status_code=403)
    if not path.exists() or not path.is_file():
        raise ApiError(code="ARTIFACT_NOT_FOUND", message="Artifact file not found.", status_code=404)
    return path


def get_artifact_download(db: Session, test_run_id: str, artifact_id: str) -> tuple[Path, str]:
    """Return (path, filename) for a single artifact, validated for safe download."""
    artifact = db.get(Artifact, artifact_id)
    if artifact is None or artifact.test_run_id != test_run_id:
        raise ApiError(code="ARTIFACT_NOT_FOUND", message="Artifact not found.", status_code=404)
    path = _safe_artifact_path(artifact.path_or_object_key)
    return path, path.name


def bundle_artifacts(db: Session, test_run_id: str) -> tuple[bytes, str]:
    """Zip all of a test run's artifacts and return (bytes, filename)."""
    tr = db.get(TestRun, test_run_id)
    if tr is None:
        raise ApiError(code="TEST_RUN_NOT_FOUND", message="Test run not found.", status_code=404)
    rows = db.scalars(select(Artifact).where(Artifact.test_run_id == test_run_id)).all()

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        seen: set[str] = set()
        for artifact in rows:
            if (artifact.size or 0) == 0:
                continue  # skip empty files (consistent with the listing)
            try:
                path = _safe_artifact_path(artifact.path_or_object_key)
            except ApiError:
                continue  # skip missing/forbidden files rather than fail the whole bundle
            arcname = path.name
            if arcname in seen:
                arcname = f"{artifact.artifact_type}_{path.name}"
            seen.add(arcname)
            zf.write(path, arcname=arcname)

    filename = f"{tr.test_id}_{test_run_id[:8]}_files.zip"
    return buffer.getvalue(), filename
