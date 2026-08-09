"""Environment compatibility tests (spec section 40)."""

from __future__ import annotations

from app.environments.matcher import evaluate_compatibility
from app.environments.models import Environment
from app.suites.models import Suite


def _suite() -> Suite:
    return Suite(
        id="demo_shaping",
        name="Demo Shaping Suite",
        requirements_json={"min_devices": 2, "traffic_generator": True, "capabilities": ["qos", "shaping"]},
        supported_platforms_json=["platform_a"],
        tests_json=["basic_pass"],
    )


def test_compatible_environment_passes() -> None:
    env = Environment(
        id="lab_23",
        name="Lab 23",
        platform="platform_a",
        capabilities_json=["qos", "shaping", "pwhe"],
        metadata_json={"traffic_generator": "ixia", "devices": [{}, {}]},
        enabled=True,
    )
    compatible, reasons = evaluate_compatibility(_suite(), env)
    assert compatible is True
    assert reasons == []


def test_missing_capability_fails() -> None:
    env = Environment(
        id="lab_x",
        name="Lab X",
        platform="platform_a",
        capabilities_json=["qos"],
        metadata_json={"traffic_generator": "ixia", "devices": [{}, {}]},
        enabled=True,
    )
    compatible, reasons = evaluate_compatibility(_suite(), env)
    assert compatible is False
    assert any("capabilities" in r for r in reasons)


def test_wrong_platform_fails() -> None:
    env = Environment(
        id="lab_c",
        name="Lab C",
        platform="platform_c",
        capabilities_json=["qos", "shaping"],
        metadata_json={"traffic_generator": "ixia", "devices": [{}, {}]},
        enabled=True,
    )
    compatible, reasons = evaluate_compatibility(_suite(), env)
    assert compatible is False
    assert any("Platform" in r for r in reasons)


def test_no_traffic_generator_fails() -> None:
    env = Environment(
        id="lab_d",
        name="Lab D",
        platform="platform_a",
        capabilities_json=["qos", "shaping"],
        metadata_json={"devices": [{}, {}]},
        enabled=True,
    )
    compatible, reasons = evaluate_compatibility(_suite(), env)
    assert compatible is False
    assert any("traffic generator" in r for r in reasons)


def test_too_few_devices_fails() -> None:
    env = Environment(
        id="lab_e",
        name="Lab E",
        platform="platform_a",
        capabilities_json=["qos", "shaping"],
        metadata_json={"traffic_generator": "ixia", "devices": [{}]},
        enabled=True,
    )
    compatible, reasons = evaluate_compatibility(_suite(), env)
    assert compatible is False
    assert any("devices" in r for r in reasons)
