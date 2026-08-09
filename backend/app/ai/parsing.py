"""Parse and validate raw AI text into an AiResult (spec section 22).

Malformed responses are rejected; the caller retries under a bounded policy.
Also enforces the safety rule that AI can never override a deterministic FAIL.
"""

from __future__ import annotations

import json
import re

from pydantic import ValidationError

from app.ai.base import AiResult
from app.core.enums import AiVerdict, TestVerdict

_JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)


class AiResponseError(Exception):
    """Raised when an AI response cannot be parsed/validated."""


def parse_ai_result(raw_text: str, test_verdict: str | None) -> AiResult:
    match = _JSON_OBJECT_RE.search(raw_text or "")
    if not match:
        raise AiResponseError("No JSON object found in AI response.")
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise AiResponseError(f"AI response was not valid JSON: {exc}") from exc

    try:
        result = AiResult.model_validate(data)
    except ValidationError as exc:
        raise AiResponseError(f"AI response did not match schema: {exc}") from exc

    # Safety guard (spec 7/23): never let AI turn a deterministic FAIL into PASSED.
    if test_verdict == TestVerdict.FAILED.value and result.ai_verdict == AiVerdict.PASSED:
        result.ai_verdict = AiVerdict.FAILED
    return result
