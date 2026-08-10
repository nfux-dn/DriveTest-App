"""Run-owned Connection Manager (spec section 51).

Owns one persistent session per required device for the lifetime of a Run. All
tests reuse these sessions via the broker/ExecutionContext; tests never open SSH.
Responsibilities: establishment, auth, command/config execution, command timeout,
bounded reconnect, session health, logging with credential masking, and cleanup.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from app.connections.devices import DeviceSpec
from app.connections.transport import Transport

logger = logging.getLogger("drivetest.connections.manager")

SecretResolver = Callable[[str], str]


class ConnectionError(Exception):
    """Raised when a device session cannot be established or used."""


@dataclass
class _DeviceConnection:
    spec: DeviceSpec
    client: Any
    # Held in memory only for reconnect; never logged or returned.
    password: str | None = field(default=None, repr=False)


def _mask(text: str, secrets: list[str]) -> str:
    masked = text
    for secret in secrets:
        if secret:
            masked = masked.replace(secret, "****")
    return masked


class ConnectionManager:
    def __init__(
        self,
        transport: Transport,
        command_timeout: float,
        reconnect_attempts: int,
        context: dict[str, str] | None = None,
    ) -> None:
        self._transport = transport
        self._command_timeout = command_timeout
        self._reconnect_attempts = max(0, reconnect_attempts)
        self._context = context or {}
        self._connections: dict[str, _DeviceConnection] = {}
        # Ordered, credential-masked record of every command + output (for artifacts).
        self._transcript: list[str] = []

    @property
    def roles(self) -> list[str]:
        return list(self._connections.keys())

    def transcript_len(self) -> int:
        return len(self._transcript)

    def transcript_since(self, start: int) -> str:
        return "\n".join(self._transcript[start:])

    def _record(self, role: str, command: str, output: str) -> None:
        entry = f"[{role}] $ {command}\n{output}".rstrip()
        self._transcript.append(entry)

    def establish(self, specs: list[DeviceSpec], secret_resolver: SecretResolver | None) -> None:
        for spec in specs:
            password = None
            if spec.secret_reference and secret_resolver is not None:
                password = secret_resolver(spec.secret_reference)
            try:
                client = self._transport.open(spec, password)
            except Exception as exc:  # noqa: BLE001 - normalize to a clean infra error
                logger.warning(
                    "connection_establish_failed role=%s host=%s transport=%s",
                    spec.role,
                    spec.host,
                    self._transport.name,
                )
                raise ConnectionError(f"Failed to connect to device '{spec.role}'.") from exc
            self._connections[spec.role] = _DeviceConnection(spec=spec, client=client, password=password)
            logger.info(
                "connection_established role=%s host=%s transport=%s %s",
                spec.role,
                spec.host,
                self._transport.name,
                self._ctx(),
            )

    def run(self, role: str, command: str) -> str:
        conn = self._require(role)
        self._ensure_alive(conn)
        secrets = [conn.password] if conn.password else []
        masked_command = _mask(command, secrets)
        logger.info("device_exec role=%s command=%s %s", role, masked_command, self._ctx())
        try:
            _status, output = self._transport.exec(conn.client, command, self._command_timeout)
        except Exception as exc:  # noqa: BLE001
            raise ConnectionError(f"Command execution failed on '{role}'.") from exc
        masked_output = _mask(output, secrets)
        self._record(role, masked_command, masked_output)
        return masked_output

    def configure(self, role: str, commands: list[str]) -> str:
        conn = self._require(role)
        self._ensure_alive(conn)
        secrets = [conn.password] if conn.password else []
        outputs: list[str] = []
        for command in commands:
            masked_command = _mask(command, secrets)
            logger.info("device_config role=%s command=%s %s", role, masked_command, self._ctx())
            try:
                _status, output = self._transport.exec(conn.client, command, self._command_timeout)
            except Exception as exc:  # noqa: BLE001
                raise ConnectionError(f"Configuration failed on '{role}'.") from exc
            masked_output = _mask(output, secrets)
            self._record(role, masked_command, masked_output)
            outputs.append(output)
        return _mask("\n".join(outputs), secrets)

    def close_all(self) -> None:
        for role, conn in self._connections.items():
            try:
                self._transport.close(conn.client)
                logger.info("connection_closed role=%s %s", role, self._ctx())
            except Exception:  # noqa: BLE001 - cleanup must not raise
                logger.warning("connection_close_error role=%s", role)
        self._connections.clear()

    def _require(self, role: str) -> _DeviceConnection:
        conn = self._connections.get(role)
        if conn is None:
            raise ConnectionError(f"Unknown device role '{role}'.")
        return conn

    def _ensure_alive(self, conn: _DeviceConnection) -> None:
        if self._transport.alive(conn.client):
            return
        # Bounded reconnect policy (spec section 51).
        for attempt in range(1, self._reconnect_attempts + 1):
            logger.info("connection_reconnect role=%s attempt=%d %s", conn.spec.role, attempt, self._ctx())
            try:
                conn.client = self._transport.open(conn.spec, conn.password)
                if self._transport.alive(conn.client):
                    return
            except Exception:  # noqa: BLE001 - try again up to the bound
                continue
        raise ConnectionError(f"Device '{conn.spec.role}' connection is down and could not be re-established.")

    def _ctx(self) -> str:
        return " ".join(f"{k}={v}" for k, v in self._context.items())
