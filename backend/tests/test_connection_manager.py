"""Connection Manager tests (spec section 51)."""

from __future__ import annotations

import pytest

from app.connections.devices import DeviceSpec
from app.connections.manager import ConnectionError, ConnectionManager
from app.connections.transport import SimulatedTransport


def _spec(role: str = "dut", secret_reference: str | None = None) -> DeviceSpec:
    return DeviceSpec(role=role, host="10.0.0.1", username="admin", port=22, secret_reference=secret_reference)


def test_establish_and_run_simulated() -> None:
    mgr = ConnectionManager(SimulatedTransport(), command_timeout=5, reconnect_attempts=1)
    mgr.establish([_spec()], secret_resolver=None)
    out = mgr.run("dut", "show interfaces description")
    assert "ge" in out  # simulated DNOS device lists ge interfaces
    assert mgr.roles == ["dut"]
    mgr.close_all()
    assert mgr.roles == []


def test_unknown_role_raises() -> None:
    mgr = ConnectionManager(SimulatedTransport(), command_timeout=5, reconnect_attempts=0)
    with pytest.raises(ConnectionError):
        mgr.run("nope", "show version")


def test_credentials_are_masked_in_output() -> None:
    # A transport that echoes the password proves masking removes it.
    class EchoPasswordTransport:
        name = "echo"

        def open(self, spec, password):
            return {"password": password, "open": True}

        def exec(self, client, command, timeout):
            return 0, f"login ok with {client['password']} running {command}"

        def alive(self, client):
            return bool(client.get("open"))

        def close(self, client):
            client["open"] = False

    mgr = ConnectionManager(EchoPasswordTransport(), command_timeout=5, reconnect_attempts=0)
    mgr.establish([_spec(secret_reference="ref-1")], secret_resolver=lambda ref: "s3cr3t")
    out = mgr.run("dut", "show run")
    assert "s3cr3t" not in out
    assert "****" in out


def test_bounded_reconnect_gives_up() -> None:
    # A transport that is never alive should fail after the bounded attempts.
    class DeadTransport(SimulatedTransport):
        def alive(self, client):
            return False

    mgr = ConnectionManager(DeadTransport(), command_timeout=5, reconnect_attempts=2)
    mgr.establish([_spec()], secret_resolver=None)
    with pytest.raises(ConnectionError):
        mgr.run("dut", "show version")
