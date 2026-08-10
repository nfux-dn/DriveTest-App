"""Per-user AI connection services: connect, read, disconnect, reveal key.

The API key is encrypted via SecretStore and referenced by the connection row;
it is only decrypted inside the backend when building the evaluator for a run.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.models import AiConnection
from app.ai.schemas import AiConnectionOut
from app.core.config import get_settings
from app.core.errors import ApiError
from app.secrets.store import SecretStore

SUPPORTED_PROVIDERS = ("openai", "anthropic")

_DEFAULT_MODEL = {
    "openai": lambda s: s.openai_model,
    "anthropic": lambda s: s.anthropic_model,
}


def get_connection(db: Session, user_id: str) -> AiConnection | None:
    return db.scalar(select(AiConnection).where(AiConnection.user_id == user_id))


def get_connection_out(db: Session, user_id: str) -> AiConnectionOut | None:
    conn = get_connection(db, user_id)
    return AiConnectionOut.model_validate(conn) if conn else None


def connect(db: Session, user_id: str, provider: str, api_key: str, model: str | None) -> AiConnectionOut:
    provider = (provider or "").lower().strip()
    if provider not in SUPPORTED_PROVIDERS:
        raise ApiError(code="AI_PROVIDER_UNSUPPORTED", message=f"Unsupported provider '{provider}'.", status_code=400)
    if not api_key.strip():
        raise ApiError(code="AI_KEY_REQUIRED", message="An API key is required.", status_code=400)

    settings = get_settings()
    resolved_model = (model or "").strip() or _DEFAULT_MODEL[provider](settings)

    store = SecretStore(db)
    conn = get_connection(db, user_id)
    if conn is not None and conn.secret_reference:
        store.delete(conn.secret_reference)
    secret_reference = store.store(api_key.strip())

    if conn is None:
        conn = AiConnection(user_id=user_id)
        db.add(conn)
    conn.provider = provider
    conn.secret_reference = secret_reference
    conn.model = resolved_model
    conn.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(conn)
    return AiConnectionOut.model_validate(conn)


def disconnect(db: Session, user_id: str) -> None:
    conn = get_connection(db, user_id)
    if conn is None:
        return
    SecretStore(db).delete(conn.secret_reference)
    db.delete(conn)
    db.commit()


def reveal_key(db: Session, user_id: str) -> str | None:
    """Backend-only: decrypt the user's AI key for building the evaluator."""
    conn = get_connection(db, user_id)
    if conn is None:
        return None
    return SecretStore(db).reveal(conn.secret_reference)
