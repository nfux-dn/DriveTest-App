"""Deterministic mock evaluator for offline dev/demo (plan open-decision D6).

It applies simple, transparent heuristics so the demo scenario (spec section 47)
behaves as documented without any network/API key:
- A deterministic FAIL is never turned into PASS.
- Obvious measurement anomalies (e.g. measured rate far above configured, or
  burst events) produce FAILED with an anomaly note.
- Otherwise PASSED. When there is no evidence at all, INCONCLUSIVE.
"""

from __future__ import annotations

from app.ai.base import AiEvidence, AiRequest, AiResult
from app.core.enums import AiVerdict, TestVerdict


class MockEvaluator:
    @property
    def model(self) -> str:
        return "mock-1"

    def evaluate(self, request: AiRequest) -> AiResult:
        anomalies = _detect_anomalies(request)

        if request.test_verdict == TestVerdict.FAILED.value:
            return AiResult(
                ai_verdict=AiVerdict.FAILED,
                confidence=0.9,
                summary="Deterministic test reported FAILED; AI concurs.",
                anomalies=anomalies,
                evidence=[AiEvidence(source="test_verdict", details="Test reported FAILED.")],
            )

        if anomalies:
            return AiResult(
                ai_verdict=AiVerdict.FAILED,
                confidence=0.86,
                summary="Measurements indicate the behavior exceeded expected bounds.",
                anomalies=anomalies,
                evidence=[AiEvidence(source="measurement", details=a) for a in anomalies],
                likely_root_cause="Shaping ceiling not enforced under burst conditions.",
                recommended_next_step="Inspect queue/shaper configuration and re-run.",
            )

        has_evidence = bool(
            request.measurements or request.observations or request.evidence or request.artifacts
        )
        if not has_evidence:
            return AiResult(
                ai_verdict=AiVerdict.INCONCLUSIVE,
                confidence=0.4,
                summary="Insufficient evidence supplied to determine a verdict.",
                recommended_next_step="Capture measurements or logs and re-run the test.",
            )

        return AiResult(
            ai_verdict=AiVerdict.PASSED,
            confidence=0.95,
            summary="Observed behavior matched the expected profile within tolerance.",
            observations=request.observations,
            evidence=[AiEvidence(source="measurement", details=str(request.measurements))]
            if request.measurements
            else [],
        )


def _detect_anomalies(request: AiRequest) -> list[str]:
    anomalies: list[str] = []
    m = request.measurements or {}

    configured = _num(m.get("configured_bandwidth_mbps"))
    measured = _num(m.get("measured_bandwidth_mbps"))
    if configured is not None and measured is not None and measured > configured * 1.05:
        anomalies.append(
            f"Measured rate {measured} Mbps exceeded configured {configured} Mbps by more than 5%."
        )

    burst = _num(m.get("burst_events"))
    if burst is not None and burst > 0:
        anomalies.append(f"{int(burst)} burst events exceeded the shaping ceiling.")

    return anomalies


def _num(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None
