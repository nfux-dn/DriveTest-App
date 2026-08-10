"""Run and test-run API schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class CreateRunRequest(BaseModel):
    suite_id: str
    values: dict[str, Any] = {}
    # Git revision. Optional in dev: when omitted, the local definitions source
    # is used so the runner can be exercised without a GitHub connection (D5/D6).
    repository: str | None = None
    branch: str | None = None
    commit: str | None = None


class TestRunOut(BaseModel):
    id: str
    test_id: str
    order_index: int
    execution_status: str
    test_verdict: str | None = None
    ai_verdict: str | None = None
    final_verdict: str | None = None
    ai_confidence: float | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    result_json: dict | None = None

    model_config = {"from_attributes": True}


class RunOut(BaseModel):
    id: str
    suite_id: str
    user_id: str
    repository: str | None = None
    branch: str | None = None
    commit_sha: str | None = None
    status: str
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class RunDetailOut(RunOut):
    tests: list[TestRunOut] = []
