"""Prerequisite template and validation schemas (spec sections 11-14).

The template is declarative (authored as YAML in the definitions source) and
parsed into these Pydantic models for machine validation.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel


class FieldType(StrEnum):
    TEXT = "text"
    TEXTAREA = "textarea"
    NUMBER = "number"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    CONFIRMATION = "confirmation"
    SELECT = "select"
    MULTISELECT = "multiselect"
    IP = "ip"
    INTERFACE = "interface"
    SECRET_REFERENCE = "secret_reference"
    CHECK = "check"


class VisibleWhen(BaseModel):
    field: str
    equals: Any


class FieldValidation(BaseModel):
    min: float | None = None
    max: float | None = None
    pattern: str | None = None
    min_length: int | None = None
    max_length: int | None = None


class CheckSpec(BaseModel):
    handler: str
    target: str | None = None
    params: dict[str, Any] = {}


class PrerequisiteField(BaseModel):
    id: str
    label: str
    description: str | None = None
    type: FieldType
    required: bool = False
    default: Any | None = None
    placeholder: str | None = None
    options: list[str] = []
    validation: FieldValidation | None = None
    visible_when: VisibleWhen | None = None
    check: CheckSpec | None = None
    remediation: str | None = None
    sensitive: bool = False
    # Device binding (spec section 51): a field carrying a device address can
    # declare the role of the device to open a Run-owned session to. The user's
    # entered value becomes the host. `credential_ref` names another field (a
    # secret_reference) holding the credential for that device.
    device_role: str | None = None
    credential_ref: str | None = None


class PrerequisiteSection(BaseModel):
    id: str
    title: str
    fields: list[PrerequisiteField] = []


class PrerequisiteTemplate(BaseModel):
    id: str
    version: int = 1
    suite_id: str
    sections: list[PrerequisiteSection] = []


class ValidateRequest(BaseModel):
    suite_id: str
    values: dict[str, Any] = {}


class FieldError(BaseModel):
    field_id: str
    message: str


class ValidateResponse(BaseModel):
    status: str  # ValidationStatus value
    errors: list[FieldError] = []
    visible_fields: list[str] = []
    pending_checks: list[str] = []


class CheckRunRequest(BaseModel):
    suite_id: str
    field_id: str
    values: dict[str, Any] = {}


class CheckRunResponse(BaseModel):
    field_id: str
    handler: str
    passed: bool
    message: str
