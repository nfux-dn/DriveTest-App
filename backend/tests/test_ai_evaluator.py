"""AI evaluator tests: mock heuristics and response parsing (spec sections 22-23)."""

from __future__ import annotations

import pytest

from app.ai.base import AiRequest
from app.ai.mock import MockEvaluator
from app.ai.parsing import AiResponseError, parse_ai_result
from app.core.enums import AiVerdict


def test_mock_passes_clean_result() -> None:
    req = AiRequest(
        test_id="basic_pass",
        test_verdict="PASSED",
        measurements={"configured_bandwidth_mbps": 1000, "measured_bandwidth_mbps": 998},
    )
    result = MockEvaluator().evaluate(req)
    assert result.ai_verdict == AiVerdict.PASSED


def test_mock_flags_anomaly_as_failed() -> None:
    req = AiRequest(
        test_id="ai_anomaly",
        test_verdict="PASSED",
        measurements={"configured_bandwidth_mbps": 1000, "measured_bandwidth_mbps": 1180, "burst_events": 7},
    )
    result = MockEvaluator().evaluate(req)
    assert result.ai_verdict == AiVerdict.FAILED
    assert result.anomalies


def test_mock_no_evidence_is_inconclusive() -> None:
    result = MockEvaluator().evaluate(AiRequest(test_id="empty", test_verdict=None))
    assert result.ai_verdict == AiVerdict.INCONCLUSIVE


def test_parse_valid_json() -> None:
    raw = '{"ai_verdict":"PASSED","confidence":0.9,"summary":"ok"}'
    result = parse_ai_result(raw, test_verdict="PASSED")
    assert result.ai_verdict == AiVerdict.PASSED
    assert result.confidence == 0.9


def test_parse_rejects_malformed() -> None:
    with pytest.raises(AiResponseError):
        parse_ai_result("not json at all", test_verdict=None)


def test_parse_never_overrides_deterministic_fail() -> None:
    # AI says PASSED but the test deterministically FAILED -> forced to FAILED.
    raw = '{"ai_verdict":"PASSED","confidence":0.99,"summary":"looks fine"}'
    result = parse_ai_result(raw, test_verdict="FAILED")
    assert result.ai_verdict == AiVerdict.FAILED
