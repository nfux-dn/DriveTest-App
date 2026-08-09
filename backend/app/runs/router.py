"""Run routes (spec section 29)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.auth.models import User
from app.db.session import get_db
from app.results import service as results_service
from app.results.schemas import RunReport
from app.runs import service
from app.runs.schemas import CreateRunRequest, RunDetailOut, RunOut, TestRunOut

router = APIRouter(prefix="/api/runs", tags=["runs"])


@router.post("", response_model=RunOut)
def create_run(
    payload: CreateRunRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> RunOut:
    return service.create_run(db, user.id, payload)


@router.get("", response_model=list[RunOut])
def list_runs(db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> list[RunOut]:
    return service.list_runs(db)


@router.get("/{run_id}", response_model=RunDetailOut)
def get_run(run_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> RunDetailOut:
    return service.get_run_detail(db, run_id)


@router.get("/{run_id}/tests", response_model=list[TestRunOut])
def list_run_tests(
    run_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)
) -> list[TestRunOut]:
    return service.list_run_tests(db, run_id)


@router.get("/{run_id}/report", response_model=RunReport)
def get_report(run_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> RunReport:
    return results_service.build_report(db, run_id)


@router.post("/{run_id}/cancel", response_model=RunOut)
def cancel_run(run_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> RunOut:
    return service.cancel_run(db, run_id)
