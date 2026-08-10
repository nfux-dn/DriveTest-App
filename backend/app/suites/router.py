"""Suite routes (spec section 29)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.auth.models import User
from app.db.session import get_db
from app.suites import service
from app.suites.schemas import SuiteOut, SuiteReadmeOut

router = APIRouter(prefix="/api/suites", tags=["suites"])


@router.get("", response_model=list[SuiteOut])
def list_suites(db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> list[SuiteOut]:
    return service.list_suites(db)


@router.get("/{suite_id}", response_model=SuiteOut)
def get_suite(suite_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> SuiteOut:
    return service.get_suite_out(db, suite_id)


@router.get("/{suite_id}/readme", response_model=SuiteReadmeOut)
def get_suite_readme(
    suite_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)
) -> SuiteReadmeOut:
    return service.get_suite_readme(db, suite_id)
