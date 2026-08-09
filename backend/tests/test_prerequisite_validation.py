"""Prerequisite validation + conditional logic tests (spec sections 12-13, 40)."""

from __future__ import annotations

from app.prerequisites.schemas import (
    PrerequisiteField,
    PrerequisiteSection,
    PrerequisiteTemplate,
)
from app.prerequisites.validation import validate_values


def _template() -> PrerequisiteTemplate:
    return PrerequisiteTemplate(
        id="t",
        version=1,
        suite_id="demo_shaping",
        sections=[
            PrerequisiteSection(
                id="connectivity",
                title="Connectivity",
                fields=[
                    PrerequisiteField(id="dut_management_ip", label="DUT IP", type="ip", required=True),
                    PrerequisiteField(id="customer_port", label="Port", type="interface", required=True),
                ],
            ),
            PrerequisiteSection(
                id="traffic",
                title="Traffic",
                fields=[
                    PrerequisiteField(
                        id="traffic_generator",
                        label="TG",
                        type="select",
                        required=True,
                        options=["ixia", "spirent"],
                    ),
                    PrerequisiteField(
                        id="ixia_chassis_ip",
                        label="Ixia Chassis IP",
                        type="ip",
                        required=True,
                        visible_when={"field": "traffic_generator", "equals": "ixia"},
                    ),
                ],
            ),
            PrerequisiteSection(
                id="physical",
                title="Physical",
                fields=[
                    PrerequisiteField(
                        id="topology_verified", label="Verified", type="confirmation", required=True
                    ),
                ],
            ),
        ],
    )


def test_valid_values_pass() -> None:
    res = validate_values(
        _template(),
        {
            "dut_management_ip": "10.0.0.1",
            "customer_port": "ge800-31/0/17",
            "traffic_generator": "ixia",
            "ixia_chassis_ip": "10.0.0.2",
            "topology_verified": True,
        },
    )
    assert res.status == "VALID"
    assert res.errors == []


def test_missing_required_ip_fails() -> None:
    res = validate_values(
        _template(),
        {
            "customer_port": "ge800-31/0/17",
            "traffic_generator": "spirent",
            "topology_verified": True,
        },
    )
    assert res.status == "INVALID"
    assert any(e.field_id == "dut_management_ip" for e in res.errors)


def test_conditional_field_hidden_when_not_ixia() -> None:
    # ixia_chassis_ip should not be required when generator is spirent.
    res = validate_values(
        _template(),
        {
            "dut_management_ip": "10.0.0.1",
            "customer_port": "ge800-31/0/17",
            "traffic_generator": "spirent",
            "topology_verified": True,
        },
    )
    assert res.status == "VALID"
    assert "ixia_chassis_ip" not in res.visible_fields


def test_conditional_field_required_when_ixia() -> None:
    res = validate_values(
        _template(),
        {
            "dut_management_ip": "10.0.0.1",
            "customer_port": "ge800-31/0/17",
            "traffic_generator": "ixia",
            "topology_verified": True,
        },
    )
    assert res.status == "INVALID"
    assert any(e.field_id == "ixia_chassis_ip" for e in res.errors)


def test_confirmation_must_be_true() -> None:
    res = validate_values(
        _template(),
        {
            "dut_management_ip": "10.0.0.1",
            "customer_port": "ge800-31/0/17",
            "traffic_generator": "spirent",
            "topology_verified": False,
        },
    )
    assert res.status == "INVALID"
    assert any(e.field_id == "topology_verified" for e in res.errors)


def test_invalid_ip_fails() -> None:
    res = validate_values(
        _template(),
        {
            "dut_management_ip": "not-an-ip",
            "customer_port": "ge800-31/0/17",
            "traffic_generator": "spirent",
            "topology_verified": True,
        },
    )
    assert res.status == "INVALID"
    assert any(e.field_id == "dut_management_ip" for e in res.errors)
