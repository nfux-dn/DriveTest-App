"""Versioned AI prompt design (spec section 23).

The prompt is strict: use only supplied evidence, never invent measurements,
return INCONCLUSIVE when evidence is insufficient, never override a deterministic
FAIL, and output only the expected JSON schema. Versions are recorded with every
evaluation so results are reproducible/auditable.
"""

from __future__ import annotations

import json

from app.ai.base import AiRequest

PROMPT_VERSION = "1.0.0"
POLICY_VERSION = "1.0.0"

SYSTEM_PROMPT = (
    "You are evaluating network equipment test evidence. Follow these rules strictly:\n"
    "1. You are evaluating network test evidence, acting as a senior network validation engineer.\n"
    "2. Use ONLY the supplied evidence. Do not assume facts that are not present.\n"
    "3. Do not invent missing measurements.\n"
    "4. If the evidence is insufficient to decide, return verdict INCONCLUSIVE.\n"
    "5. Explain exactly why you reached the verdict.\n"
    "6. Cite evidence from the supplied result/logs in the evidence array.\n"
    "7. Never override a deterministic FAIL: if the test itself reported FAILED, you must not return PASSED.\n"
    "8. Output ONLY a single JSON object matching the required schema, with no extra text.\n\n"
    "Required JSON schema (keys and value types):\n"
    "{\n"
    '  "ai_verdict": "PASSED" | "FAILED" | "INCONCLUSIVE",\n'
    '  "confidence": number between 0 and 1,\n'
    '  "summary": string,\n'
    '  "observations": string[],\n'
    '  "anomalies": string[],\n'
    '  "evidence": [{"source": string, "details": string}],\n'
    '  "likely_root_cause": string | null,\n'
    '  "recommended_next_step": string | null\n'
    "}\n"
)


def build_user_content(request: AiRequest) -> str:
    """Serialize the curated request into the user message."""
    payload = {
        "test_id": request.test_id,
        "test_name": request.test_name,
        "description": request.description,
        "expected_behavior": request.expected_behavior,
        "evaluation_instructions": request.evaluation_instructions,
        "deterministic_test_verdict": request.test_verdict,
        "measurements": request.measurements,
        "observations": request.observations,
        "evidence": request.evidence,
        "artifacts": request.artifacts,
        "logs": {
            "stdout_excerpt": request.stdout_excerpt,
            "stderr_excerpt": request.stderr_excerpt,
        },
        "environment": {
            "platform": request.platform,
            "system_type": request.system_type,
            "software_version": request.software_version,
        },
    }
    return (
        "Evaluate the following test evidence and return the JSON verdict object.\n\n"
        + json.dumps(payload, indent=2, default=str)
    )
