# Demo Shaping Suite

A self-contained demonstration suite (spec section 47). It contains four tests:

- `basic_pass` — deterministic `test_verdict = PASSED`.
- `ai_anomaly` — deterministic `test_verdict = PASSED`; later phases have AI flag an anomaly.
- `ai_judged` — `test_verdict = null`; the verdict is punted to AI (later phases).
- `script_error` — intentionally crashes to demonstrate `SCRIPT_ERROR` classification.

Each test writes its result to the path in the `DRIVETEST_RESULT_PATH` environment
variable, following the standard result contract (spec section 20).
