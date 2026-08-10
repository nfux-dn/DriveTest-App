"""Deterministic mock evaluator for offline dev/demo (plan open-decision D6).

It reviews the gathered files against the expected results with simple, transparent
heuristics so the demo (spec section 47) behaves without any network/API key:
- A deterministic FAIL is never turned into PASS.
- Error signatures in the gathered files (e.g. `ERROR:`, `Traceback`, `% Invalid`)
  fail the test.
- Obvious measurement anomalies (measured rate far above configured, or burst
  events) fail the test.
- Otherwise PASSED. With no files/evidence at all, INCONCLUSIVE.

A real provider (openai/anthropic) reads the files + expected results directly.
"""

from __future__ import annotations

from app.ai.base import AiEvidence, AiRequest, AiResult
from app.core.enums import AiVerdict, TestVerdict

_ERROR_SIGNATURES = ("error:", "traceback", "% invalid", "syntax error", "failed to")


class MockEvaluator:
    @property
    def model(self) -> str:
        return "mock-1"

    def evaluate(self, request: AiRequest) -> AiResult:
        anomalies = _detect_anomalies(request)
        file_findings = _scan_files(request)

        if request.test_verdict == TestVerdict.FAILED.value:
            return AiResult(
                ai_verdict=AiVerdict.FAILED,
                confidence=0.9,
                summary="Deterministic test reported FAILED; AI concurs after reviewing the files.",
                anomalies=anomalies + file_findings,
                evidence=[AiEvidence(source="test_verdict", details="Test reported FAILED.")],
            )

        if file_findings:
            return AiResult(
                ai_verdict=AiVerdict.FAILED,
                confidence=0.88,
                summary="The gathered files show error/failure signatures against the expected results.",
                anomalies=file_findings,
                evidence=[AiEvidence(source="files", details=f) for f in file_findings],
                recommended_next_step="Inspect the session transcript / stderr for the reported error.",
            )

        if anomalies:
            return AiResult(
                ai_verdict=AiVerdict.FAILED,
                confidence=0.86,
                summary="File evidence indicates behavior outside the expected bounds.",
                anomalies=anomalies,
                evidence=[AiEvidence(source="measurement", details=a) for a in anomalies],
                likely_root_cause="Behavior did not match the expected results.",
                recommended_next_step="Review the result.json/session against the expected results.",
            )

        has_files = bool(request.files)
        has_evidence = has_files or bool(
            request.measurements or request.observations or request.evidence
        )
        if not has_evidence:
            return AiResult(
                ai_verdict=AiVerdict.INCONCLUSIVE,
                confidence=0.4,
                summary="No files or evidence were gathered; cannot determine a verdict.",
                recommended_next_step="Capture a session transcript or result and re-run the test.",
            )

        reviewed = ", ".join(sorted(request.files.keys())) or "reported result"
        return AiResult(
            ai_verdict=AiVerdict.PASSED,
            confidence=0.95,
            summary="Reviewed the gathered files against the expected results; they match.",
            observations=request.observations,
            evidence=[AiEvidence(source="files", details=f"Reviewed: {reviewed}")],
        )


def _scan_files(request: AiRequest) -> list[str]:
    findings: list[str] = []
    for name, content in (request.files or {}).items():
        low = (content or "").lower()
        for sig in _ERROR_SIGNATURES:
            if sig in low:
                findings.append(f"'{sig.strip()}' found in {name}.")
                break
    return findings


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
