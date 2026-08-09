"""Automatic prerequisite check handlers (spec section 15).

Only registered handlers can run. YAML never supplies arbitrary commands. Each
handler receives the resolved target/params plus the current field values and
returns (passed, message).

For the MVP these are lightweight reachability checks (TCP connect). They can be
extended later with real SSH/device interaction behind the same registry.
"""

from __future__ import annotations

import logging
import re
import socket
from collections.abc import Callable

from app.prerequisites.schemas import CheckSpec

logger = logging.getLogger("drivetest.prerequisites.checks")

CheckHandler = Callable[[dict, dict], tuple[bool, str]]

_PLACEHOLDER_RE = re.compile(r"\$\{([a-zA-Z0-9_]+)\}")


def _resolve_placeholders(text: str, values: dict) -> str:
    def repl(match: re.Match) -> str:
        return str(values.get(match.group(1), ""))

    return _PLACEHOLDER_RE.sub(repl, text)


def _tcp_reachable(host: str, port: int, timeout: float = 5.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def check_ssh_connectivity(params: dict, values: dict) -> tuple[bool, str]:
    host = params.get("target")
    port = int(params.get("port", 22))
    if not host:
        return False, "No target host resolved for SSH check."
    ok = _tcp_reachable(host, port)
    return (ok, f"SSH port {port} on {host} is reachable." if ok else f"Cannot reach {host}:{port}.")


def check_tcp_port(params: dict, values: dict) -> tuple[bool, str]:
    host = params.get("target")
    port = int(params.get("port", 0))
    if not host or not port:
        return False, "Host and port are required for TCP check."
    ok = _tcp_reachable(host, port)
    return (ok, f"{host}:{port} is reachable." if ok else f"Cannot reach {host}:{port}.")


def check_traffic_generator_reachable(params: dict, values: dict) -> tuple[bool, str]:
    host = params.get("target")
    port = int(params.get("port", 443))
    if not host:
        return False, "No traffic generator address resolved."
    ok = _tcp_reachable(host, port)
    return (ok, f"Traffic generator {host} is reachable." if ok else f"Cannot reach {host}:{port}.")


CHECK_HANDLERS: dict[str, CheckHandler] = {
    "ssh_connectivity": check_ssh_connectivity,
    "tcp_port": check_tcp_port,
    "traffic_generator_reachable": check_traffic_generator_reachable,
}


def run_check(spec: CheckSpec, values: dict) -> tuple[bool, str]:
    handler = CHECK_HANDLERS.get(spec.handler)
    if handler is None:
        return False, f"Unknown check handler '{spec.handler}'."
    params = dict(spec.params)
    if spec.target is not None:
        params["target"] = _resolve_placeholders(spec.target, values)
    logger.info("running_check handler=%s target=%s", spec.handler, params.get("target"))
    try:
        return handler(params, values)
    except Exception as exc:  # noqa: BLE001 - convert to a clean failed check result
        logger.exception("check_handler_error handler=%s", spec.handler)
        return False, f"Check raised an error: {exc}"
