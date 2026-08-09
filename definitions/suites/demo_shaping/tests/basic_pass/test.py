"""Demo test: deterministic PASS (spec section 47, Test 1).

Writes a standard result.json (spec section 20) to DRIVETEST_RESULT_PATH.
"""

import json
import os


def main() -> None:
    result = {
        "execution_status": "COMPLETED",
        "test_id": os.environ.get("DRIVETEST_TEST_ID", "basic_pass"),
        "test_verdict": "PASSED",
        "measurements": {
            "configured_bandwidth_mbps": 1000,
            "measured_bandwidth_mbps": 998,
        },
        "observations": ["Queue stayed within configured shaping range."],
        "evidence": ["show qos queue statistics output"],
        "artifacts": [],
    }
    print("basic_pass: measured 998 Mbps against 1000 Mbps target")
    with open(os.environ["DRIVETEST_RESULT_PATH"], "w", encoding="utf-8") as fh:
        json.dump(result, fh)


if __name__ == "__main__":
    main()
