"""OpenAI and Anthropic evaluators using httpx (no extra SDK dependency).

Both send the versioned system+user prompt and parse the JSON response with a
bounded retry policy (spec sections 22-23). Secrets (API keys) are never logged.
Neither provider is required for dev; the mock evaluator is the default.
"""

from __future__ import annotations

import logging
import time

import httpx

from app.ai.base import AiRequest, AiResult
from app.ai.parsing import AiResponseError, parse_ai_result
from app.ai.prompts import SYSTEM_PROMPT, build_user_content
from app.core.config import Settings

logger = logging.getLogger("drivetest.ai.providers")

_TRANSIENT_STATUS = {429, 500, 502, 503, 504}


class _HttpEvaluatorBase:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def _call_model(self, request: AiRequest) -> str:  # pragma: no cover - network
        raise NotImplementedError

    def evaluate(self, request: AiRequest) -> AiResult:
        retries = max(0, self._settings.ai_max_retries)
        last_error: Exception | None = None
        for attempt in range(retries + 1):
            try:
                raw = self._call_model(request)
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code
                last_error = exc
                if status in _TRANSIENT_STATUS and attempt < retries:
                    delay = 2 ** attempt
                    logger.warning(
                        "ai_http_transient status=%s attempt=%d model=%s retry_in=%ss",
                        status, attempt + 1, self.model, delay,
                    )
                    time.sleep(delay)
                    continue
                raise AiResponseError(f"AI provider HTTP {status}: {exc.response.text[:200]}") from exc
            except httpx.HTTPError as exc:  # network/timeout
                last_error = exc
                if attempt < retries:
                    time.sleep(2 ** attempt)
                    continue
                raise AiResponseError(f"AI provider request failed: {exc}") from exc

            try:
                return parse_ai_result(raw, request.test_verdict)
            except AiResponseError as exc:
                last_error = exc
                logger.warning("ai_response_invalid attempt=%d model=%s", attempt + 1, self.model)
        raise AiResponseError(f"AI evaluation failed after {retries + 1} attempts: {last_error}")


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


class CursorEvaluator:
    """Evaluator backed by the `cursor-agent` CLI (Composer models).

    Runs the CLI headlessly in read-only "ask" mode (`--mode ask --force`), which
    returns the model's text; we parse that as the JSON verdict. The CLI is used
    directly (not the SDK local runtime, which can't bypass the workspace-trust
    prompt in a headless container).
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    @property
    def model(self) -> str:
        return self._settings.cursor_model or "cursor-default"

    def evaluate(self, request: AiRequest) -> AiResult:
        import os
        import shutil
        import subprocess
        import tempfile

        exe = shutil.which("cursor-agent")
        if not exe:
            raise AiResponseError(
                "Cursor CLI ('cursor-agent') is not installed in the backend image."
            )
        if not self._settings.cursor_api_key:
            raise AiResponseError("No Cursor API key configured for this user.")

        prompt = SYSTEM_PROMPT + "\n\n" + build_user_content(request)
        cmd = [exe, "-p", "--force", "--mode", "ask", "--output-format", "text"]
        if self._settings.cursor_model:
            cmd += ["--model", self._settings.cursor_model]
        cmd += [prompt]

        env = {**os.environ, "CURSOR_API_KEY": self._settings.cursor_api_key}
        timeout = self._settings.cursor_timeout_seconds
        retries = max(0, self._settings.ai_max_retries)
        last_error: Exception | None = None

        for attempt in range(retries + 1):
            try:
                proc = subprocess.run(
                    cmd,
                    cwd=tempfile.mkdtemp(prefix="drivetest-ai-"),
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                )
            except subprocess.TimeoutExpired as exc:
                raise AiResponseError(f"Cursor agent timed out after {timeout}s.") from exc
            if proc.returncode != 0:
                raise AiResponseError(
                    f"Cursor agent exited {proc.returncode}: {(proc.stderr or '').strip()[:300]}"
                )
            try:
                return parse_ai_result(proc.stdout, request.test_verdict)
            except AiResponseError as exc:
                last_error = exc
                logger.warning("ai_response_invalid attempt=%d model=cursor", attempt + 1)

        raise AiResponseError(f"Cursor AI response invalid after {retries + 1} attempts: {last_error}")


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
