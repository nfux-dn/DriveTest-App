"""Prerequisite services: resolve template, validate values, run checks."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import ApiError
from app.environments.service import get_environment
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


def resolve_for(db: Session, suite_id: str, environment_id: str) -> PrerequisiteTemplate:
    get_suite(db, suite_id)  # ensures suite exists
    env = get_environment(db, environment_id)
    return resolve_template(
        get_settings().definitions_path,
        suite_id=suite_id,
        platform=env.platform,
        system_type=env.system_type,
    )


def validate(db: Session, suite_id: str, environment_id: str, values: dict) -> ValidateResponse:
    template = resolve_for(db, suite_id, environment_id)
    return validate_values(template, values)


def _find_check_field(template: PrerequisiteTemplate, field_id: str) -> PrerequisiteField:
    for section in template.sections:
        for field in section.fields:
            if field.id == field_id:
                return field
    raise ApiError(code="PREREQUISITE_FIELD_NOT_FOUND", message="Field not found in template.", status_code=404)


def run_field_check(
    db: Session, suite_id: str, environment_id: str, field_id: str, values: dict
) -> CheckRunResponse:
    template = resolve_for(db, suite_id, environment_id)
    field = _find_check_field(template, field_id)
    if field.check is None:
        raise ApiError(code="NOT_A_CHECK_FIELD", message="Field has no check handler.", status_code=400)
    passed, message = run_check(field.check, values)
    return CheckRunResponse(field_id=field_id, handler=field.check.handler, passed=passed, message=message)
