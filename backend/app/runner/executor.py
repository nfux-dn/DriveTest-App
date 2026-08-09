"""Execute a single test in a separate Python process (spec section 19).

Test code NEVER runs inside the API process. The runner launches `python
test.py`, passes context via files/env, enforces a timeout, captures bounded
stdout/stderr, reads result.json, and classifies the execution outcome.
"""

from __future__ import annotations

import json
import logging
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.core.enums import ExecutionStatus
from app.runner.result_contract import TestResultContract, parse_result

logger = logging.getLogger("drivetest.runner.executor")


@dataclass
class ExecOutcome:
    execution_status: ExecutionStatus
    test_verdict: str | None
    result_json: dict[str, Any] | None
    stdout: str
    stderr: str
    exit_code: int | None
    error_detail: str | None = None
    artifacts: list[str] = field(default_factory=list)


def _truncate(data: str, limit: int) -> str:
    if len(data) <= limit:
        return data
    return data[:limit] + f"\n...[truncated, {len(data) - limit} more bytes]"


def execute_test(
    test_dir: Path,
    test_id: str,
    context: dict[str, Any],
    results_dir: Path,
    timeout_seconds: int,
    max_capture_bytes: int,
    extra_env: dict[str, str] | None = None,
) -> ExecOutcome:
    test_script = test_dir / "test.py"
    if not test_script.exists():
        return ExecOutcome(
            execution_status=ExecutionStatus.SCRIPT_ERROR,
            test_verdict=None,
            result_json=None,
            stdout="",
            stderr="",
            exit_code=None,
            error_detail=f"test.py not found for test '{test_id}'.",
        )

    result_path = results_dir / f"{test_id}.result.json"
    context_path = results_dir / f"{test_id}.context.json"
    with context_path.open("w", encoding="utf-8") as fh:
        json.dump(context, fh)

    env = {
        "DRIVETEST_RESULT_PATH": str(result_path),
        "DRIVETEST_CONTEXT_PATH": str(context_path),
        "DRIVETEST_TEST_ID": test_id,
        "PATH": _safe_path(),
        "PYTHONUNBUFFERED": "1",
    }
    # Broker URL/token and SDK path (spec section 51) — never credentials.
    if extra_env:
        env.update(extra_env)

    logger.info("test_start test_id=%s", test_id)
    try:
        proc = subprocess.run(
            ["python3", "test.py"],
            cwd=str(test_dir),
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        logger.warning("test_timeout test_id=%s", test_id)
        return ExecOutcome(
            execution_status=ExecutionStatus.TIMEOUT,
            test_verdict=None,
            result_json=None,
            stdout=_truncate(exc.stdout or "", max_capture_bytes) if isinstance(exc.stdout, str) else "",
            stderr=_truncate(exc.stderr or "", max_capture_bytes) if isinstance(exc.stderr, str) else "",
            exit_code=None,
            error_detail=f"Test exceeded timeout of {timeout_seconds}s.",
        )

    stdout = _truncate(proc.stdout or "", max_capture_bytes)
    stderr = _truncate(proc.stderr or "", max_capture_bytes)

    if proc.returncode != 0:
        logger.warning("test_nonzero_exit test_id=%s code=%s", test_id, proc.returncode)
        return ExecOutcome(
            execution_status=ExecutionStatus.SCRIPT_ERROR,
            test_verdict=None,
            result_json=_maybe_read_json(result_path),
            stdout=stdout,
            stderr=stderr,
            exit_code=proc.returncode,
            error_detail=f"Process exited with code {proc.returncode}.",
        )

    raw = _maybe_read_json(result_path)
    if raw is None:
        return ExecOutcome(
            execution_status=ExecutionStatus.SCRIPT_ERROR,
            test_verdict=None,
            result_json=None,
            stdout=stdout,
            stderr=stderr,
            exit_code=proc.returncode,
            error_detail="Test produced no valid result.json.",
        )

    contract: TestResultContract | None = parse_result(raw)
    if contract is None:
        return ExecOutcome(
            execution_status=ExecutionStatus.SCRIPT_ERROR,
            test_verdict=None,
            result_json=raw,
            stdout=stdout,
            stderr=stderr,
            exit_code=proc.returncode,
            error_detail="result.json did not match the required schema.",
        )

    logger.info(
        "test_done test_id=%s status=%s verdict=%s",
        test_id,
        contract.execution_status,
        contract.test_verdict,
    )
    return ExecOutcome(
        execution_status=contract.execution_status,
        test_verdict=contract.test_verdict.value if contract.test_verdict else None,
        result_json=contract.model_dump(mode="json"),
        stdout=stdout,
        stderr=stderr,
        exit_code=proc.returncode,
        artifacts=contract.artifacts,
    )


def _maybe_read_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else None
    except (json.JSONDecodeError, OSError):
        return None


def _safe_path() -> str:
    return "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
