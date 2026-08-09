"""Final verdict engine (spec sections 7-8).

This is THE authoritative business rule. It must not be duplicated in the
frontend (spec section 41). A deterministic test FAIL can never become PASSED.

Truth table (test_verdict, ai_verdict) -> final:
    PASSED, PASSED        -> PASSED
    FAILED, PASSED        -> FAILED
    PASSED, FAILED        -> FAILED
    FAILED, FAILED        -> FAILED
    None,   PASSED        -> PASSED
    None,   FAILED        -> FAILED
    PASSED, INCONCLUSIVE  -> REVIEW_REQUIRED
    FAILED, INCONCLUSIVE  -> FAILED
    None,   INCONCLUSIVE  -> REVIEW_REQUIRED
"""

from __future__ import annotations

from app.core.enums import AiVerdict, ExecutionStatus, FinalVerdict, TestVerdict


def compute_final_verdict(test_verdict: str | None, ai_verdict: str) -> FinalVerdict:
    """Apply the exact truth table for a COMPLETED test."""
    if ai_verdict == AiVerdict.INCONCLUSIVE.value:
        if test_verdict == TestVerdict.FAILED.value:
            return FinalVerdict.FAILED
        return FinalVerdict.REVIEW_REQUIRED

    if ai_verdict == AiVerdict.PASSED.value and test_verdict in (
        TestVerdict.PASSED.value,
        None,
    ):
        return FinalVerdict.PASSED

    return FinalVerdict.FAILED


def final_verdict_for_test(
    execution_status: str,
    test_verdict: str | None,
    ai_verdict: str | None,
) -> FinalVerdict | None:
    """Full rule including execution state (spec section 8).

    If execution did not COMPLETE, there is no product verdict (and it can never
    be PASSED); we return None and callers surface the execution_status instead.
    """
    if execution_status != ExecutionStatus.COMPLETED.value:
        return None
    if ai_verdict is None:
        return None
    return compute_final_verdict(test_verdict, ai_verdict)
