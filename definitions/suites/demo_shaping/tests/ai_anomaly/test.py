"""Demo test: deterministic PASS with a subtle anomaly (spec section 47, Test 2).

The test itself reports PASSED; in later phases the AI reviewer is expected to
notice the anomaly and disagree.
"""

import json
import os


def main() -> None:
    result = {
        "execution_status": "COMPLETED",
        "test_id": os.environ.get("DRIVETEST_TEST_ID", "ai_anomaly"),
        "test_verdict": "PASSED",
        "measurements": {
            "configured_bandwidth_mbps": 1000,
            "measured_bandwidth_mbps": 1180,
            "burst_events": 7,
        },
        "observations": [
            "Average rate within range, but repeated bursts exceeded the shaping ceiling.",
        ],
        "evidence": ["burst counter incremented 7 times during the run"],
        "artifacts": [],
    }
    print("ai_anomaly: average within range; 7 burst events above ceiling")
    with open(os.environ["DRIVETEST_RESULT_PATH"], "w", encoding="utf-8") as fh:
        json.dump(result, fh)


if __name__ == "__main__":
    main()
