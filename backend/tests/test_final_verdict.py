"""Final verdict truth-table tests (spec sections 7, 41).

These are the most important tests in the system; the backend is authoritative.
"""

from __future__ import annotations

import pytest

from app.core.enums import ExecutionStatus, FinalVerdict
from app.evaluation.verdict import compute_final_verdict, final_verdict_for_test


def final(test_verdict, ai_verdict) -> str:
    return compute_final_verdict(test_verdict, ai_verdict).value


def test_truth_table_exact() -> None:
    assert final("PASSED", "PASSED") == "PASSED"
    assert final("FAILED", "PASSED") == "FAILED"
    assert final("PASSED", "FAILED") == "FAILED"
    assert final("FAILED", "FAILED") == "FAILED"
    assert final(None, "PASSED") == "PASSED"
    assert final(None, "FAILED") == "FAILED"
    assert final("PASSED", "INCONCLUSIVE") == "REVIEW_REQUIRED"
    assert final(None, "INCONCLUSIVE") == "REVIEW_REQUIRED"
    assert final("FAILED", "INCONCLUSIVE") == "FAILED"


@pytest.mark.parametrize(
    "status",
    ["SCRIPT_ERROR", "INFRA_ERROR", "TIMEOUT", "CANCELLED", "SKIPPED", "PENDING", "RUNNING"],
)
def test_non_completed_execution_has_no_product_verdict(status: str) -> None:
    # Regardless of any (stale) verdicts, a non-COMPLETED execution is never PASSED.
    assert final_verdict_for_test(status, "PASSED", "PASSED") is None


def test_completed_without_ai_is_pending() -> None:
    assert final_verdict_for_test(ExecutionStatus.COMPLETED.value, "PASSED", None) is None


def test_completed_with_ai_uses_truth_table() -> None:
    assert (
        final_verdict_for_test(ExecutionStatus.COMPLETED.value, None, "PASSED")
        == FinalVerdict.PASSED
    )
    assert (
        final_verdict_for_test(ExecutionStatus.COMPLETED.value, "PASSED", "INCONCLUSIVE")
        == FinalVerdict.REVIEW_REQUIRED
    )
