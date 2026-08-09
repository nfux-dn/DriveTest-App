"""OpenAI and Anthropic evaluators using httpx (no extra SDK dependency).

Both send the versioned system+user prompt and parse the JSON response with a
bounded retry policy (spec sections 22-23). Secrets (API keys) are never logged.
Neither provider is required for dev; the mock evaluator is the default.
"""

from __future__ import annotations

import logging

import httpx

from app.ai.base import AiRequest, AiResult
from app.ai.parsing import AiResponseError, parse_ai_result
from app.ai.prompts import SYSTEM_PROMPT, build_user_content
from app.core.config import Settings

logger = logging.getLogger("drivetest.ai.providers")


class _HttpEvaluatorBase:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def _call_model(self, request: AiRequest) -> str:  # pragma: no cover - network
        raise NotImplementedError

    def evaluate(self, request: AiRequest) -> AiResult:
        retries = max(0, self._settings.ai_max_retries)
        last_error: Exception | None = None
        for attempt in range(retries + 1):
            raw = self._call_model(request)
            try:
                return parse_ai_result(raw, request.test_verdict)
            except AiResponseError as exc:
                last_error = exc
                logger.warning("ai_response_invalid attempt=%d model=%s", attempt + 1, self.model)
        raise AiResponseError(f"AI response invalid after {retries + 1} attempts: {last_error}")


class OpenAIEvaluator(_HttpEvaluatorBase):
    @property
    def model(self) -> str:
        return self._settings.openai_model

    def _call_model(self, request: AiRequest) -> str:  # pragma: no cover - network
        url = f"{self._settings.openai_base_url}/chat/completions"
        headers = {"Authorization": f"Bearer {self._settings.openai_api_key}"}
        body = {
            "model": self._settings.openai_model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_user_content(request)},
            ],
            "temperature": 0,
            "response_format": {"type": "json_object"},
        }
        with httpx.Client(timeout=self._settings.ai_request_timeout_seconds) as client:
            resp = client.post(url, headers=headers, json=body)
            resp.raise_for_status()
            data = resp.json()
        return data["choices"][0]["message"]["content"]


class AnthropicEvaluator(_HttpEvaluatorBase):
    @property
    def model(self) -> str:
        return self._settings.anthropic_model

    def _call_model(self, request: AiRequest) -> str:  # pragma: no cover - network
        url = f"{self._settings.anthropic_base_url}/messages"
        headers = {
            "x-api-key": self._settings.anthropic_api_key,
            "anthropic-version": "2023-06-01",
        }
        body = {
            "model": self._settings.anthropic_model,
            "max_tokens": 1024,
            "temperature": 0,
            "system": SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": build_user_content(request)}],
        }
        with httpx.Client(timeout=self._settings.ai_request_timeout_seconds) as client:
            resp = client.post(url, headers=headers, json=body)
            resp.raise_for_status()
            data = resp.json()
        return data["content"][0]["text"]
