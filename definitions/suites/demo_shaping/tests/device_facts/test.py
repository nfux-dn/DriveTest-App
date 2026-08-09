"""Demo test using the DriveTest Network API (spec section 51).

This test does NOT open its own SSH connection. It uses the Run-owned session via
the ExecutionContext, so it never sees device hosts or credentials.
"""

from drivetest import ExecutionContext


def main() -> None:
    ctx = ExecutionContext.from_env()

    # Reuse the Run-owned connection to the DUT (established at run start).
    output = ctx.device("dut").run("show version")
    print(output)

    passed = "ok" in output.lower()
    ctx.write_result(
        {
            "execution_status": "COMPLETED",
            "test_id": ctx.test_id or "device_facts",
            "test_verdict": "PASSED" if passed else "FAILED",
            "measurements": {"command": "show version"},
            "observations": ["Collected device version via the DriveTest Network API."],
            "evidence": [output.strip().splitlines()[-1] if output.strip() else "no output"],
            "artifacts": [],
        }
    )


if __name__ == "__main__":
    main()
