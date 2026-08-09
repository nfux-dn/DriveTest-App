"""Suite read services and mapping to API schema."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.suites.models import Suite
from app.suites.schemas import SuiteOut, SuiteRequirements


def _to_out(suite: Suite) -> SuiteOut:
    return SuiteOut(
        id=suite.id,
        name=suite.name,
        description=suite.description,
        requirements=SuiteRequirements(**(suite.requirements_json or {})),
        supported_platforms=suite.supported_platforms_json or [],
        tests=suite.tests_json or [],
    )


def list_suites(db: Session) -> list[SuiteOut]:
    suites = db.scalars(select(Suite).order_by(Suite.name)).all()
    return [_to_out(s) for s in suites]


def get_suite(db: Session, suite_id: str) -> Suite:
    suite = db.get(Suite, suite_id)
    if suite is None:
        raise ApiError(code="SUITE_NOT_FOUND", message="Suite not found.", status_code=404)
    return suite


def get_suite_out(db: Session, suite_id: str) -> SuiteOut:
    return _to_out(get_suite(db, suite_id))
