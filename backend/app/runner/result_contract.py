"""Standard result contract (spec section 20).

Each test writes a result.json matching this schema. The runner validates it;
a malformed result is treated as a SCRIPT_ERROR (spec section 8/19).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ValidationError

from app.core.enums import ExecutionStatus, TestVerdict


class TestResultContract(BaseModel):
    execution_status: ExecutionStatus = ExecutionStatus.COMPLETED
    test_id: str
    # test_verdict may be null when the test punts the verdict to AI (spec 5).
    test_verdict: TestVerdict | None = None
    measurements: dict[str, Any] = {}
    observations: list[str] = []
    evidence: list[Any] = []
    artifacts: list[str] = []


def parse_result(data: dict) -> TestResultContract | None:
    """Return a validated contract, or None if the structure is invalid."""
    try:
        return TestResultContract.model_validate(data)
    except ValidationError:
        return None
