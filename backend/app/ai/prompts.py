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
    "You are a senior network validation engineer independently reviewing a completed test. "
    "Your job is to reach your OWN verdict from raw evidence, not to trust the script's self-report. "
    "Follow these rules strictly:\n"
    "1. Base your verdict ONLY on the INDEPENDENT LOGS gathered during the run: the device session\n"
    "   transcript (session.txt), stdout, stderr, and any other log files provided. Compare what these\n"
    "   logs actually show against the EXPECTED RESULTS for the test.\n"
    "2. The test script's own result.json, its self-reported verdict, and its self-reported measurements\n"
    "   are NOT evidence. Do NOT use them to justify a PASS, and do NOT simply restate them. You must\n"
    "   independently confirm the expected behavior in the raw logs themselves.\n"
    "3. Use ONLY the supplied logs. Do not assume or invent facts that are not present in them.\n"
    "4. If the logs are insufficient to independently confirm the expected behavior, return INCONCLUSIVE.\n"
    "5. Explain exactly why you reached the verdict, quoting concrete lines from the logs.\n"
    "6. Cite concrete evidence from the supplied logs (with the source file name) in the evidence array.\n"
    "7. Safety guard: never override a deterministic FAIL. A `deterministic_test_verdict` of FAILED is\n"
    "   provided solely so you never return PASSED in that case; it is not evidence of a pass.\n"
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
    """Serialize the curated request into the user message.

    The AI reviews `independent_logs` against `expected_results` and must reach its
    own verdict from those logs. The script's own result.json / measurements are NOT
    included as evidence. Only `deterministic_test_verdict` is passed, purely to
    enforce the never-override-a-FAIL safety rule.
    """
    payload = {
        "test_id": request.test_id,
        "expected_results": {
            "description": request.description,
            "expected_behavior": request.expected_behavior,
            "evaluation_instructions": request.evaluation_instructions,
        },
        "independent_logs": request.files,
        "safety_guard_only": {
            "deterministic_test_verdict": request.test_verdict,
            "note": (
                "Provided only so you never return PASSED when this is FAILED. "
                "This is NOT evidence; judge the logs yourself."
            ),
        },
        "environment": {
            "platform": request.platform,
            "system_type": request.system_type,
            "software_version": request.software_version,
        },
    }
    return (
        "Independently review the logs below and compare what they actually show against the "
        "expected results, then return the JSON verdict object. Do not trust or restate the "
        "test script's own result.json.\n\n"
        + json.dumps(payload, indent=2, default=str)
    )


def build_cursor_user_content(request: AiRequest, log_filenames: list[str]) -> str:
    """User prompt for the Cursor CLI when logs are attached as files on disk.

    The bulky independent logs (device session transcript, stdout, stderr,
    result.json) are written to files in the agent's workspace and read there via
    its file tools, instead of being inlined into the command-line argument (which
    overflows the OS ARG_MAX limit). Only the expected results (from evaluation.md)
    plus a pointer to the attached files travel in the prompt.
    """
    payload = {
        "test_id": request.test_id,
        "expected_results": {
            "description": request.description,
            "expected_behavior": request.expected_behavior,
            "evaluation_instructions": request.evaluation_instructions,
        },
        "safety_guard_only": {
            "deterministic_test_verdict": request.test_verdict,
            "note": (
                "Provided only so you never return PASSED when this is FAILED. "
                "This is NOT evidence; judge the logs yourself."
            ),
        },
        "environment": {
            "platform": request.platform,
            "system_type": request.system_type,
            "software_version": request.software_version,
        },
    }
    if log_filenames:
        files_block = "\n".join(f"- {name}" for name in log_filenames)
        logs_intro = (
            "The run's INDEPENDENT LOGS are attached as files in your current workspace "
            "directory. Read each of them IN FULL with your file tools before judging:\n"
            f"{files_block}\n\n"
        )
    else:
        logs_intro = (
            "No independent log files were captured for this run. If you cannot confirm the "
            "expected behavior, return INCONCLUSIVE.\n\n"
        )
    return (
        logs_intro
        + "Compare what those logs actually show against the expected results below, then "
        "return the JSON verdict object. Do not trust or restate the test script's own "
        "result.json.\n\n"
        + json.dumps(payload, indent=2, default=str)
    )
