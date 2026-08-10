# Demo Shaping Suite

## Suite details

A self-contained demonstration suite (spec section 47). It contains:

- `device_facts` - uses the Run-owned device connection via ExecutionContext.
- `basic_pass` - deterministic `test_verdict = PASSED`.
- `ai_anomaly` - deterministic `PASSED`; the AI reviewer flags an anomaly.
- `ai_judged` - `test_verdict = null`; the verdict is punted to AI.
- `script_error` - intentionally crashes to demonstrate `SCRIPT_ERROR`.

Provide the device in the Environment tab: enter the **DUT Management IP** (opened as role
`dut`). Each test writes a standard result (spec section 20).

## Connectivity

```text
        +-------------------+
        |   DUT (role: dut) |
        +---------+---------+
                  |
             management network
                  |
             +----+-----+
             | DriveTest |
             +----------+
```

- Connect the DUT management port to the management network reachable by DriveTest.
- Enter the DUT management IP in the Environment tab; SSH must be enabled.
