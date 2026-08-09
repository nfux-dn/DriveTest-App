"""Select the configured AI evaluator (spec section 6, plan open-decision D2).

Defaults to the offline mock. If a real provider is configured but its API key is
missing, we fall back to the mock and log a warning rather than failing runs.
"""

from __future__ import annotations

import logging

from app.ai.base import Evaluator
from app.ai.mock import MockEvaluator
from app.ai.providers import AnthropicEvaluator, OpenAIEvaluator
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

    return MockEvaluator()
