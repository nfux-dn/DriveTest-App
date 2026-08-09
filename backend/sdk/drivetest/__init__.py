"""DriveTest test SDK — the ExecutionContext / Network API (spec section 51).

Test scripts use this instead of opening their own SSH connections. It talks to
the Run-owned connection broker over localhost using only the Python standard
library, so tests need no third-party dependencies.

Typical usage inside a test.py:

    from drivetest import ExecutionContext

    ctx = ExecutionContext.from_env()
    version = ctx.device("dut").run("show version")
    ctx.device("dut").configure(["configure terminal", "interface ...", "end"])
    ctx.write_result({"test_id": ctx.test_id, "test_verdict": "PASSED"})
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

__all__ = ["ExecutionContext", "Device", "DriveTestApiError"]


class DriveTestApiError(RuntimeError):
    """Raised when a device command via the DriveTest Network API fails."""


class Device:
    def __init__(self, ctx: "ExecutionContext", role: str) -> None:
        self._ctx = ctx
        self._role = role

    def run(self, command: str, timeout: float = 60.0) -> str:
        """Execute a command on the device and return its output."""
        data = self._ctx._post("/exec", {"role": self._role, "command": command}, timeout)
        return data.get("output", "")

    def configure(self, commands: list[str], commit: bool = False, timeout: float = 120.0) -> str:
        """Enter config mode and stage a candidate (spec section 51).

        Sends `configure`, then each line, and optionally `commit`. Does not
        commit unless commit=True; pair with commit() when you want to review or
        run additional steps before applying.
        """
        lines = ["configure", *commands]
        if commit:
            lines.append("commit")
        data = self._ctx._post("/config", {"role": self._role, "commands": lines}, timeout)
        return data.get("output", "")

    def commit(self, timeout: float = 120.0) -> str:
        """Commit the staged candidate configuration."""
        data = self._ctx._post("/exec", {"role": self._role, "command": "commit"}, timeout)
        return data.get("output", "")

    def rollback(self, rollback_id: int = 1, timeout: float = 120.0) -> str:
        """Load a previous committed configuration (0=current, 1=previous, ...).

        Follow with commit() to apply the rollback.
        """
        data = self._ctx._post(
            "/exec", {"role": self._role, "command": f"rollback {int(rollback_id)}"}, timeout
        )
        return data.get("output", "")


class ExecutionContext:
    def __init__(self, broker_url: str, token: str, context: dict[str, Any], result_path: str | None) -> None:
        self._broker_url = broker_url.rstrip("/")
        self._token = token
        self._context = context
        self._result_path = result_path

    @classmethod
    def from_env(cls) -> "ExecutionContext":
        broker_url = os.environ.get("DRIVETEST_BROKER_URL", "")
        token = os.environ.get("DRIVETEST_BROKER_TOKEN", "")
        result_path = os.environ.get("DRIVETEST_RESULT_PATH")
        context: dict[str, Any] = {}
        context_path = os.environ.get("DRIVETEST_CONTEXT_PATH")
        if context_path and os.path.exists(context_path):
            with open(context_path, encoding="utf-8") as fh:
                context = json.load(fh)
        return cls(broker_url=broker_url, token=token, context=context, result_path=result_path)

    # --- context accessors -------------------------------------------------
    @property
    def run_id(self) -> str | None:
        return self._context.get("run_id")

    @property
    def suite_id(self) -> str | None:
        return self._context.get("suite_id")

    @property
    def test_id(self) -> str | None:
        return self._context.get("test_id") or os.environ.get("DRIVETEST_TEST_ID")

    @property
    def environment(self) -> dict[str, Any]:
        return self._context.get("environment", {})

    @property
    def values(self) -> dict[str, Any]:
        """Prerequisite values the user supplied (never contains raw secrets)."""
        return self._context.get("values", {})

    def device(self, role: str) -> Device:
        return Device(self, role)

    def write_result(self, result: dict[str, Any]) -> None:
        """Convenience helper to write the standard result.json (spec section 20)."""
        if not self._result_path:
            raise DriveTestApiError("DRIVETEST_RESULT_PATH is not set.")
        with open(self._result_path, "w", encoding="utf-8") as fh:
            json.dump(result, fh)

    # --- internal ----------------------------------------------------------
    def _post(self, path: str, payload: dict[str, Any], timeout: float) -> dict[str, Any]:
        if not self._broker_url:
            raise DriveTestApiError("No connection broker is available for this run.")
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self._broker_url}{path}",
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._token}",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read() or b"{}")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise DriveTestApiError(f"Device API error ({exc.code}): {detail}") from exc
        except urllib.error.URLError as exc:
            raise DriveTestApiError(f"Could not reach the DriveTest device API: {exc}") from exc
