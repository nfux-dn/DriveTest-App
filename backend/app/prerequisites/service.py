"""Prerequisite services: resolve template, validate values, run checks.

Prerequisites are suite-scoped (spec sections 10-14): one prerequisite file per
suite. Device details are entered by the user in the Environment tab.
"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import ApiError
from app.prerequisites.checks import run_check
from app.prerequisites.loader import resolve_template
from app.prerequisites.schemas import (
    CheckRunResponse,
    PrerequisiteField,
    PrerequisiteTemplate,
    ValidateResponse,
)
from app.prerequisites.validation import validate_values
from app.suites.service import get_suite


def resolve_for(db: Session, suite_id: str) -> PrerequisiteTemplate:
    suite = get_suite(db, suite_id)  # ensures the suite exists
    definitions_dir = get_settings().definitions_path
    source = suite.source_path or f"suites/{suite_id}"
    prereq_file = Path(definitions_dir) / source / "prerequisites.yaml"
    return resolve_template(prereq_file, suite_id=suite_id)


def validate(db: Session, suite_id: str, values: dict) -> ValidateResponse:
    template = resolve_for(db, suite_id)
    return validate_values(template, values)


def _find_check_field(template: PrerequisiteTemplate, field_id: str) -> PrerequisiteField:
    for section in template.sections:
        for field in section.fields:
            if field.id == field_id:
                return field
    raise ApiError(code="PREREQUISITE_FIELD_NOT_FOUND", message="Field not found in template.", status_code=404)


def run_field_check(db: Session, suite_id: str, field_id: str, values: dict) -> CheckRunResponse:
    template = resolve_for(db, suite_id)
    field = _find_check_field(template, field_id)
    if field.check is None:
        raise ApiError(code="NOT_A_CHECK_FIELD", message="Field has no check handler.", status_code=400)
    passed, message = run_check(field.check, values)
    return CheckRunResponse(field_id=field_id, handler=field.check.handler, passed=passed, message=message)
