"""Test-run result routes (spec section 29)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.auth.models import User
from app.db.session import get_db
from app.results import service
from app.results.schemas import ArtifactOut, TestRunDetailOut

router = APIRouter(prefix="/api/test-runs", tags=["results"])


@router.get("/{test_run_id}", response_model=TestRunDetailOut)
def get_test_run(
    test_run_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)
) -> TestRunDetailOut:
    return service.get_test_run(db, test_run_id)


@router.get("/{test_run_id}/artifacts", response_model=list[ArtifactOut])
def list_artifacts(
    test_run_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)
) -> list[ArtifactOut]:
    return service.list_artifacts(db, test_run_id)
