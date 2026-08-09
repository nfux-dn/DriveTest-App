"""Backend validation of prerequisite values (spec sections 11-13).

The backend never trusts frontend validation. Conditional fields (visible_when)
are evaluated here so hidden fields are not required.
"""

from __future__ import annotations

import ipaddress
import re

from app.prerequisites.schemas import (
    FieldError,
    FieldType,
    PrerequisiteField,
    PrerequisiteTemplate,
    ValidateResponse,
)

# A permissive interface-name pattern (e.g. ge800-31/0/17, GigabitEthernet0/0/1).
_INTERFACE_RE = re.compile(r"^[A-Za-z][A-Za-z0-9]*[-]?\d+([/:.]\d+)*$")


def _iter_fields(template: PrerequisiteTemplate):
    for section in template.sections:
        for field in section.fields:
            yield field


def is_visible(field: PrerequisiteField, values: dict) -> bool:
    if field.visible_when is None:
        return True
    return values.get(field.visible_when.field) == field.visible_when.equals


def validate_values(template: PrerequisiteTemplate, values: dict) -> ValidateResponse:
    errors: list[FieldError] = []
    visible_fields: list[str] = []
    pending_checks: list[str] = []

    for field in _iter_fields(template):
        if not is_visible(field, values):
            continue
        visible_fields.append(field.id)

        if field.type == FieldType.CHECK:
            # Checks are executed via a separate endpoint; flag as pending here.
            if field.required:
                pending_checks.append(field.id)
            continue

        raw = values.get(field.id)
        missing = raw is None or (isinstance(raw, str) and raw.strip() == "")

        if missing:
            if field.required:
                errors.append(FieldError(field_id=field.id, message=f"{field.label} is required."))
            continue

        error = _validate_field_value(field, raw)
        if error:
            errors.append(FieldError(field_id=field.id, message=error))

    status = "VALID" if not errors else "INVALID"
    return ValidateResponse(
        status=status,
        errors=errors,
        visible_fields=visible_fields,
        pending_checks=pending_checks,
    )


def _validate_field_value(field: PrerequisiteField, raw) -> str | None:
    t = field.type
    if t == FieldType.IP:
        try:
            ipaddress.ip_address(str(raw))
        except ValueError:
            return f"{field.label} must be a valid IP address."
    elif t == FieldType.INTERFACE:
        if not _INTERFACE_RE.match(str(raw)):
            return f"{field.label} must be a valid interface name."
    elif t == FieldType.INTEGER:
        if not _is_integer(raw):
            return f"{field.label} must be an integer."
        else:
            return _range_error(field, float(raw))
    elif t == FieldType.NUMBER:
        if not _is_number(raw):
            return f"{field.label} must be a number."
        else:
            return _range_error(field, float(raw))
    elif t in (FieldType.BOOLEAN, FieldType.CONFIRMATION):
        if not isinstance(raw, bool):
            return f"{field.label} must be true or false."
        if t == FieldType.CONFIRMATION and field.required and raw is not True:
            return f"{field.label} must be confirmed."
    elif t == FieldType.SELECT:
        if field.options and str(raw) not in field.options:
            return f"{field.label} must be one of {field.options}."
    elif t == FieldType.MULTISELECT:
        if not isinstance(raw, list):
            return f"{field.label} must be a list."
        invalid = [v for v in raw if field.options and v not in field.options]
        if invalid:
            return f"{field.label} contains invalid options: {invalid}."
    elif t in (FieldType.TEXT, FieldType.TEXTAREA, FieldType.SECRET_REFERENCE):
        return _text_error(field, str(raw))
    return None


def _text_error(field: PrerequisiteField, value: str) -> str | None:
    v = field.validation
    if v is None:
        return None
    if v.min_length is not None and len(value) < v.min_length:
        return f"{field.label} must be at least {v.min_length} characters."
    if v.max_length is not None and len(value) > v.max_length:
        return f"{field.label} must be at most {v.max_length} characters."
    if v.pattern is not None and not re.match(v.pattern, value):
        return f"{field.label} has an invalid format."
    return None


def _range_error(field: PrerequisiteField, value: float) -> str | None:
    v = field.validation
    if v is None:
        return None
    if v.min is not None and value < v.min:
        return f"{field.label} must be >= {v.min}."
    if v.max is not None and value > v.max:
        return f"{field.label} must be <= {v.max}."
    return None


def _is_integer(raw) -> bool:
    if isinstance(raw, bool):
        return False
    if isinstance(raw, int):
        return True
    try:
        int(str(raw))
        return True
    except ValueError:
        return False


def _is_number(raw) -> bool:
    if isinstance(raw, bool):
        return False
    try:
        float(str(raw))
        return True
    except ValueError:
        return False
