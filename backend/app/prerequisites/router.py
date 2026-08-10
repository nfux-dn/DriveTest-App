"""Prerequisite routes (spec section 29). Suite-scoped."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.auth.models import User
from app.db.session import get_db
from app.prerequisites import service
from app.prerequisites.schemas import (
    CheckRunRequest,
    CheckRunResponse,
    PrerequisiteTemplate,
    ValidateRequest,
    ValidateResponse,
)

router = APIRouter(prefix="/api", tags=["prerequisites"])


@router.get("/suites/{suite_id}/prerequisites", response_model=PrerequisiteTemplate)
def get_prerequisites(
    suite_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> PrerequisiteTemplate:
    return service.resolve_for(db, suite_id)


@router.post("/prerequisites/validate", response_model=ValidateResponse)
def validate_prerequisites(
    payload: ValidateRequest, db: Session = Depends(get_db), _: User = Depends(get_current_user)
) -> ValidateResponse:
    return service.validate(db, payload.suite_id, payload.values)


@router.post("/prerequisites/checks/{field_id}/run", response_model=CheckRunResponse)
def run_check(
    field_id: str,
    payload: CheckRunRequest,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> CheckRunResponse:
    return service.run_field_check(db, payload.suite_id, field_id, payload.values)
