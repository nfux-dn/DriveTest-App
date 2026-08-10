"""Select the configured AI evaluator (spec section 6, plan open-decision D2).

Defaults to the offline mock. If a real provider is configured but its API key is
missing, we fall back to the mock and log a warning rather than failing runs.
"""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.ai.base import Evaluator
from app.ai.mock import MockEvaluator
from app.ai.providers import AnthropicEvaluator, CursorEvaluator, OpenAIEvaluator
from app.core.config import Settings, get_settings

logger = logging.getLogger("drivetest.ai.factory")


def get_evaluator(settings: Settings | None = None) -> Evaluator:
    settings = settings or get_settings()
    provider = (settings.ai_provider or "mock").lower()

    if provider == "openai":
        if not settings.openai_api_key:
            logger.warning("openai_key_missing falling_back=mock")
            return MockEvaluator()
        return OpenAIEvaluator(settings)

    if provider == "anthropic":
        if not settings.anthropic_api_key:
            logger.warning("anthropic_key_missing falling_back=mock")
            return MockEvaluator()
        return AnthropicEvaluator(settings)

    if provider == "cursor":
        if not settings.cursor_api_key:
            logger.warning("cursor_key_missing falling_back=mock")
            return MockEvaluator()
        return CursorEvaluator(settings)

    return MockEvaluator()


def get_evaluator_for_user(db: Session, user_id: str, settings: Settings | None = None) -> Evaluator:
    """Prefer the run user's own AI connection; fall back to global config/mock.

    The user's key is decrypted here (backend-only) and injected into an effective
    Settings copy so the provider clients use per-user credentials.
    """
    settings = settings or get_settings()
    # Imported lazily to avoid a circular import (connection_service -> secrets/db).
    from app.ai import connection_service

    conn = connection_service.get_connection(db, user_id)
    if conn is None:
        return get_evaluator(settings)

    key = connection_service.reveal_key(db, user_id)
    if not key:
        return get_evaluator(settings)

    if conn.provider == "openai":
        effective = settings.model_copy(
            update={"ai_provider": "openai", "openai_api_key": key, "openai_model": conn.model or settings.openai_model}
        )
    elif conn.provider == "anthropic":
        effective = settings.model_copy(
            update={
                "ai_provider": "anthropic",
                "anthropic_api_key": key,
                "anthropic_model": conn.model or settings.anthropic_model,
            }
        )
    elif conn.provider == "cursor":
        effective = settings.model_copy(
            update={
                "ai_provider": "cursor",
                "cursor_api_key": key,
                "cursor_model": conn.model or settings.cursor_model,
            }
        )
    else:
        return get_evaluator(settings)

    logger.info("ai_evaluator_per_user user_id=%s provider=%s", user_id, conn.provider)
    return get_evaluator(effective)
