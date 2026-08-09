"""Result schema validation tests (spec sections 20, 40)."""

from __future__ import annotations

from app.runner.result_contract import parse_result


def test_valid_deterministic_result() -> None:
    result = parse_result(
        {
            "execution_status": "COMPLETED",
            "test_id": "basic_pass",
            "test_verdict": "PASSED",
            "measurements": {"measured_bandwidth_mbps": 998},
        }
    )
    assert result is not None
    assert result.test_verdict.value == "PASSED"


def test_null_verdict_is_allowed() -> None:
    result = parse_result(
        {"execution_status": "COMPLETED", "test_id": "ai_judged", "test_verdict": None}
    )
    assert result is not None
    assert result.test_verdict is None


def test_missing_test_id_is_invalid() -> None:
    assert parse_result({"execution_status": "COMPLETED", "test_verdict": "PASSED"}) is None


def test_bad_verdict_is_invalid() -> None:
    assert parse_result({"test_id": "x", "test_verdict": "MAYBE"}) is None
