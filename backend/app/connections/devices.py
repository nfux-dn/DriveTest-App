"""Resolve which devices a Run must connect to (spec section 51).

Device sessions are prerequisite-driven (spec sections 11-14): each prerequisite
field that declares a `device_role` opens one Run-owned session to the host the
user entered for that field. The number of such filled, visible fields therefore
determines how many sessions open. Credentials are referenced (never inlined) via
a `credential_ref` field holding a secret reference.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import get_settings
from app.prerequisites.schemas import PrerequisiteTemplate
from app.prerequisites.validation import is_visible


@dataclass
class DeviceSpec:
    role: str
    host: str
    username: str
    port: int
    secret_reference: str | None = None


def resolve_required_devices(template: PrerequisiteTemplate, values: dict) -> list[DeviceSpec]:
    """Build one DeviceSpec per visible, filled prerequisite field with a device_role."""
    settings = get_settings()
    specs: list[DeviceSpec] = []
    seen_roles: set[str] = set()

    for section in template.sections:
        for field in section.fields:
            if not field.device_role:
                continue
            if not is_visible(field, values):
                continue
            host = values.get(field.id)
            if host is None or (isinstance(host, str) and not host.strip()):
                continue
            if field.device_role in seen_roles:
                continue
            seen_roles.add(field.device_role)

            secret_reference = values.get(field.credential_ref) if field.credential_ref else None
            specs.append(
                DeviceSpec(
                    role=field.device_role,
                    host=str(host),
                    username=settings.ssh_default_username,
                    port=settings.ssh_port,
                    secret_reference=secret_reference,
                )
            )
    return specs
