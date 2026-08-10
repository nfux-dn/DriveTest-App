"""AI provider connection routes (per-user keys)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.ai import connection_service as service
from app.ai.schemas import AiConnectionOut, AiConnectRequest
from app.auth.deps import get_current_user
from app.auth.models import User
from app.db.session import get_db

router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.get("/connection", response_model=AiConnectionOut | None)
def get_connection(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> AiConnectionOut | None:
    return service.get_connection_out(db, user.id)


@router.post("/connect", response_model=AiConnectionOut)
def connect(
    payload: AiConnectRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> AiConnectionOut:
    return service.connect(db, user.id, payload.provider, payload.api_key, payload.model)


@router.post("/disconnect")
def disconnect(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict[str, bool]:
    service.disconnect(db, user.id)
    return {"ok": True}
