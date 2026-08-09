"""Check handler tests (spec section 15)."""

from __future__ import annotations

from app.prerequisites.checks import CHECK_HANDLERS, run_check
from app.prerequisites.schemas import CheckSpec


def test_placeholder_resolution_and_unknown_handler() -> None:
    spec = CheckSpec(handler="does_not_exist", target="${dut_management_ip}")
    passed, message = run_check(spec, {"dut_management_ip": "10.0.0.1"})
    assert passed is False
    assert "Unknown check handler" in message


def test_registry_contains_expected_handlers() -> None:
    assert "ssh_connectivity" in CHECK_HANDLERS
    assert "traffic_generator_reachable" in CHECK_HANDLERS
    assert "tcp_port" in CHECK_HANDLERS


def test_tcp_check_missing_target_fails_cleanly() -> None:
    spec = CheckSpec(handler="tcp_port", params={"port": 22})
    passed, message = run_check(spec, {})
    assert passed is False
    assert "required" in message.lower()
