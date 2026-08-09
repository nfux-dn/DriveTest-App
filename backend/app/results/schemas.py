"""Result API schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.runs.schemas import TestRunOut

__all__ = [
    "TestRunOut",
    "ArtifactOut",
    "AiEvaluationOut",
    "TestRunDetailOut",
    "RunReport",
]


class ArtifactOut(BaseModel):
    id: str
    artifact_type: str
    path_or_object_key: str
    size: int | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AiEvaluationOut(BaseModel):
    model: str
    prompt_version: str
    policy_version: str
    ai_verdict: str
    confidence: float | None = None
    summary: str | None = None
    analysis: dict[str, Any] = {}


class TestRunDetailOut(TestRunOut):
    """A test run plus its AI review (spec sections 35-36)."""

    ai: AiEvaluationOut | None = None


class RunReport(BaseModel):
    """Suite run summary (spec Phase 10, section 48)."""

    run_id: str
    suite_id: str
    environment_id: str
    user_id: str
    status: str
    repository: str | None = None
    branch: str | None = None
    commit_sha: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    total: int
    passed: int
    failed: int
    review_required: int
    script_error: int
    infra_error: int
    timeout: int
    other: int
    tests: list[TestRunOut] = []
