"""Run services: create runs (with validation) and read run state."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.enums import RunStatus, ValidationStatus
from app.core.errors import ApiError
from app.git.validators import validate_full_name, validate_ref, validate_sha
from app.prerequisites.models import PrerequisiteInstance
from app.prerequisites.service import validate as validate_prerequisites
from app.results.models import TestRun
from app.runs.models import Run
from app.runs.orchestrator import start_run_async
from app.runs.schemas import CreateRunRequest, RunDetailOut, RunOut, TestRunOut
from app.suites.service import get_suite

logger = logging.getLogger("drivetest.runs.service")


def create_run(db: Session, user_id: str, payload: CreateRunRequest) -> RunOut:
    suite = get_suite(db, payload.suite_id)

    # Backend re-validates prerequisites; block execution if invalid (spec 4).
    validation = validate_prerequisites(db, payload.suite_id, payload.values)
    if validation.status != ValidationStatus.VALID.value:
        raise ApiError(
            code="PREREQUISITES_INVALID",
            message="Prerequisites are not satisfied.",
            status_code=400,
            details=[e.model_dump() for e in validation.errors],
        )

    repository = validate_full_name(payload.repository) if payload.repository else None
    branch = validate_ref(payload.branch) if payload.branch else None
    commit = validate_sha(payload.commit) if payload.commit else None

    # Git single-source-of-truth: when the caller didn't pick an explicit repo, run
    # the platform suites repo at the latest commit on its branch (resolved and
    # pinned at launch). In local dev mode we leave these unset (run from disk).
    settings = get_settings()
    if repository is None and settings.definitions_source == "git":
        repository = validate_full_name(settings.suites_repository)
        branch = validate_ref(branch or settings.suites_branch)

    run = Run(
        suite_id=payload.suite_id,
        user_id=user_id,
        repository=repository,
        branch=branch,
        commit_sha=commit,
        status=RunStatus.PENDING.value,
    )
    db.add(run)
    db.flush()

    db.add(
        PrerequisiteInstance(
            run_id=run.id,
            template_version=1,
            values_json=payload.values,
            validation_status=ValidationStatus.VALID.value,
        )
    )

    for index, test_id in enumerate(suite.tests_json or []):
        db.add(TestRun(run_id=run.id, test_id=test_id, order_index=index))

    db.commit()
    db.refresh(run)

    start_run_async(run.id)
    logger.info("run_created run_id=%s suite=%s", run.id, payload.suite_id)
    return RunOut.model_validate(run)


def list_runs(db: Session) -> list[RunOut]:
    runs = db.scalars(select(Run).order_by(Run.created_at.desc())).all()
    return [RunOut.model_validate(r) for r in runs]


def get_run(db: Session, run_id: str) -> Run:
    run = db.get(Run, run_id)
    if run is None:
        raise ApiError(code="RUN_NOT_FOUND", message="Run not found.", status_code=404)
    return run


def get_run_detail(db: Session, run_id: str) -> RunDetailOut:
    run = get_run(db, run_id)
    tests = _tests_for_run(db, run_id)
    detail = RunDetailOut.model_validate(run)
    detail.tests = tests
    return detail


def list_run_tests(db: Session, run_id: str) -> list[TestRunOut]:
    get_run(db, run_id)
    return _tests_for_run(db, run_id)


def _tests_for_run(db: Session, run_id: str) -> list[TestRunOut]:
    rows = db.scalars(
        select(TestRun).where(TestRun.run_id == run_id).order_by(TestRun.order_index)
    ).all()
    return [TestRunOut.model_validate(t) for t in rows]


def cancel_run(db: Session, run_id: str) -> RunOut:
    run = get_run(db, run_id)
    if run.status in (RunStatus.COMPLETED.value, RunStatus.FAILED.value, RunStatus.CANCELLED.value):
        raise ApiError(code="RUN_NOT_CANCELLABLE", message="Run has already finished.", status_code=400)
    run.status = RunStatus.CANCELLED.value
    run.finished_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(run)
    return RunOut.model_validate(run)
