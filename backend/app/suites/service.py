"""Suite read services and mapping to API schema."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import ApiError
from app.suites.models import Suite
from app.suites.schemas import SuiteOut, SuiteReadmeOut


def _to_out(suite: Suite) -> SuiteOut:
    return SuiteOut(
        id=suite.id,
        name=suite.name,
        description=suite.description,
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


def get_suite_readme(db: Session, suite_id: str) -> SuiteReadmeOut:
    """Read the suite's README (purpose + connectivity) from the definitions source."""
    suite = get_suite(db, suite_id)
    markdown = ""
    if suite.source_path:
        definitions_dir = get_settings().definitions_path
        # source_path is relative to the definitions dir; guard against traversal.
        readme = (definitions_dir / suite.source_path / "README.md").resolve()
        try:
            readme.relative_to(definitions_dir.resolve())
        except ValueError:
            readme = None  # outside the definitions dir; ignore
        if readme and readme.exists():
            markdown = readme.read_text(encoding="utf-8")
    return SuiteReadmeOut(suite_id=suite_id, markdown=markdown)
