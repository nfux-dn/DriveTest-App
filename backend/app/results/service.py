"""Result read services for individual test runs and their artifacts."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.results.models import Artifact, TestRun
from app.results.schemas import ArtifactOut
from app.runs.schemas import TestRunOut


def get_test_run(db: Session, test_run_id: str) -> TestRunOut:
    tr = db.get(TestRun, test_run_id)
    if tr is None:
        raise ApiError(code="TEST_RUN_NOT_FOUND", message="Test run not found.", status_code=404)
    return TestRunOut.model_validate(tr)


def list_artifacts(db: Session, test_run_id: str) -> list[ArtifactOut]:
    if db.get(TestRun, test_run_id) is None:
        raise ApiError(code="TEST_RUN_NOT_FOUND", message="Test run not found.", status_code=404)
    rows = db.scalars(select(Artifact).where(Artifact.test_run_id == test_run_id)).all()
    return [ArtifactOut.model_validate(a) for a in rows]
