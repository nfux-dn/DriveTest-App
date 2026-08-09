"""Pluggable device transports (spec section 51).

`SimulatedTransport` is the default so the platform runs without live devices.
`SshTransport` uses paramiko for real labs. Both expose the same tiny surface so
the ConnectionManager does not care which is in use. paramiko is imported lazily
so the app works even when it is not installed and the simulated transport is used.
"""

from __future__ import annotations

import logging
from typing import Any, Protocol

from app.connections.devices import DeviceSpec

logger = logging.getLogger("drivetest.connections.transport")


class Transport(Protocol):
    name: str

    def open(self, spec: DeviceSpec, password: str | None) -> Any: ...

    def exec(self, client: Any, command: str, timeout: float) -> tuple[int, str]: ...

    def alive(self, client: Any) -> bool: ...

    def close(self, client: Any) -> None: ...


class SimulatedTransport:
    """Deterministic, offline transport for dev/demo. Never touches the network."""

    name = "simulated"

    def open(self, spec: DeviceSpec, password: str | None) -> Any:
        logger.info("sim_open role=%s host=%s", spec.role, spec.host)
        return {"role": spec.role, "host": spec.host, "open": True}

    def exec(self, client: Any, command: str, timeout: float) -> tuple[int, str]:
        role = client.get("role", "device")
        output = f"[simulated {role}] $ {command}\nok\n"
        return 0, output

    def alive(self, client: Any) -> bool:
        return bool(client and client.get("open"))

    def close(self, client: Any) -> None:
        if isinstance(client, dict):
            client["open"] = False


class SshTransport:
    """Real SSH transport backed by paramiko."""

    name = "ssh"

    def __init__(self, connect_timeout: float) -> None:
        self._connect_timeout = connect_timeout

    def open(self, spec: DeviceSpec, password: str | None) -> Any:
        import paramiko  # lazy import

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            hostname=spec.host,
            port=spec.port,
            username=spec.username,
            password=password,
            timeout=self._connect_timeout,
            allow_agent=False,
            look_for_keys=False,
        )
        return client

    def exec(self, client: Any, command: str, timeout: float) -> tuple[int, str]:
        _stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
        out = stdout.read().decode("utf-8", errors="replace")
        err = stderr.read().decode("utf-8", errors="replace")
        exit_status = stdout.channel.recv_exit_status()
        combined = out + (f"\n[stderr]\n{err}" if err else "")
        return exit_status, combined

    def alive(self, client: Any) -> bool:
        transport = client.get_transport() if client else None
        return bool(transport and transport.is_active())

    def close(self, client: Any) -> None:
        try:
            client.close()
        except Exception:  # noqa: BLE001 - closing must never raise
            logger.warning("ssh_close_error")


def get_transport() -> Transport:
    from app.core.config import get_settings

    settings = get_settings()
    if settings.ssh_transport == "ssh":
        return SshTransport(connect_timeout=settings.ssh_connect_timeout_seconds)
    return SimulatedTransport()
