"""Simulated DNOS device + prerequisite-driven device resolution (spec section 51)."""

from __future__ import annotations

from app.connections.devices import DeviceSpec, resolve_required_devices
from app.connections.transport import SimulatedDnosDevice
from app.prerequisites.schemas import (
    PrerequisiteField,
    PrerequisiteSection,
    PrerequisiteTemplate,
)


def _device() -> SimulatedDnosDevice:
    return SimulatedDnosDevice(DeviceSpec(role="dut", host="10.0.0.1", username="admin", port=22))


def _parse(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in text.splitlines():
        low = line.lower()
        if not line.strip() or (low.startswith("interface") and "description" in low):
            continue
        parts = line.split(None, 3)
        out[parts[0]] = parts[3].strip() if len(parts) > 3 else ""
    return out


def test_show_lists_seeded_ge_interfaces() -> None:
    out = _device().handle("show interfaces description")
    parsed = _parse(out)
    assert any(name.startswith("ge") for name in parsed)


def test_configure_commit_then_rollback_restores_baseline() -> None:
    d = _device()
    baseline = _parse(d.handle("show interfaces description"))
    assert baseline["ge100-0/0/0"] == ""

    for line in ["configure", "interfaces", "ge100-0/0/0", 'description "uplink"', "!", "!", "commit"]:
        d.handle(line)

    after = _parse(d.handle("show interfaces description"))
    assert after["ge100-0/0/0"] == "uplink"

    d.handle("rollback 1")
    d.handle("commit")
    reverted = _parse(d.handle("show interfaces description"))
    assert reverted["ge100-0/0/0"] == baseline["ge100-0/0/0"]


def test_unknown_command_returns_ok() -> None:
    assert "ok" in _device().handle("show version").lower()


def _template(fields: list[PrerequisiteField]) -> PrerequisiteTemplate:
    return PrerequisiteTemplate(
        id="t",
        suite_id="s",
        sections=[PrerequisiteSection(id="c", title="Connectivity", fields=fields)],
    )


def test_resolve_devices_only_from_device_role_fields() -> None:
    tmpl = _template(
        [
            PrerequisiteField(id="dut_management_ip", label="DUT", type="ip", required=True, device_role="dut"),
            PrerequisiteField(id="note", label="Note", type="text"),
        ]
    )
    specs = resolve_required_devices(tmpl, {"dut_management_ip": "10.0.0.1", "note": "x"})
    assert [s.role for s in specs] == ["dut"]
    assert specs[0].host == "10.0.0.1"


def test_prerequisite_structure_controls_session_count() -> None:
    tmpl = _template(
        [
            PrerequisiteField(id="dut_management_ip", label="DUT", type="ip", device_role="dut"),
            PrerequisiteField(
                id="mse_management_ip",
                label="MSE",
                type="ip",
                device_role="mse",
                visible_when={"field": "has_mse", "equals": True},
            ),
        ]
    )
    # Only dut filled and visible -> one session.
    one = resolve_required_devices(tmpl, {"dut_management_ip": "10.0.0.1"})
    assert {s.role for s in one} == {"dut"}

    # mse becomes visible and filled -> two sessions.
    two = resolve_required_devices(
        tmpl, {"dut_management_ip": "10.0.0.1", "mse_management_ip": "10.0.0.2", "has_mse": True}
    )
    assert {s.role for s in two} == {"dut", "mse"}
