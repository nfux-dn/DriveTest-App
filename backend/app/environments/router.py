"""Environment routes (spec section 29)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.auth.models import User
from app.db.session import get_db
from app.environments import service
from app.environments.schemas import EnvironmentOut

router = APIRouter(prefix="/api/environments", tags=["environments"])


@router.get("", response_model=list[EnvironmentOut])
def list_environments(
    db: Session = Depends(get_db), _: User = Depends(get_current_user)
) -> list[EnvironmentOut]:
    return service.list_environments(db)


@router.get("/{environment_id}", response_model=EnvironmentOut)
def get_environment(
    environment_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)
) -> EnvironmentOut:
    return service.get_environment_out(db, environment_id)
