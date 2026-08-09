"""AI evaluator abstraction (spec sections 6, 21-23).

`AiRequest` is the curated input given to the evaluator (only relevant info, with
size limits). `AiResult` is the structured output every evaluator must return.
`Evaluator` is the provider-agnostic protocol; implementations live alongside
(mock, openai, anthropic) and are selected by the factory.
"""

from __future__ import annotations

from typing import Any, Protocol

from pydantic import BaseModel, Field

from app.core.enums import AiVerdict


class AiRequest(BaseModel):
    test_id: str
    # Test definition/instructions and expected behavior (from test.yaml if present).
    test_name: str | None = None
    description: str | None = None
    expected_behavior: str | None = None
    evaluation_instructions: str | None = None
    # The deterministic result the test produced (may be null verdict, spec 5).
    test_verdict: str | None = None
    measurements: dict[str, Any] = {}
    observations: list[str] = []
    evidence: list[Any] = []
    artifacts: list[str] = []
    # Selected, size-limited log excerpts (spec 21).
    stdout_excerpt: str | None = None
    stderr_excerpt: str | None = None
    # Platform/system metadata.
    platform: str | None = None
    system_type: str | None = None
    software_version: str | None = None


class AiEvidence(BaseModel):
    source: str
    details: str


class AiResult(BaseModel):
    ai_verdict: AiVerdict
    confidence: float = Field(ge=0.0, le=1.0)
    summary: str
    observations: list[str] = []
    anomalies: list[str] = []
    evidence: list[AiEvidence] = []
    likely_root_cause: str | None = None
    recommended_next_step: str | None = None


class Evaluator(Protocol):
    """Every AI provider implements this surface."""

    @property
    def model(self) -> str: ...

    def evaluate(self, request: AiRequest) -> AiResult: ...
