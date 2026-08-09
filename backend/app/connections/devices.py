"""Resolve which devices a Run must connect to (spec section 51).

Devices come from the Environment's metadata. Each entry has a role and either a
static host or a `host_from_value` naming a prerequisite field to read the host
from. Credentials are referenced (never inlined) via `secret_reference`.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import get_settings
from app.environments.models import Environment


@dataclass
class DeviceSpec:
    role: str
    host: str
    username: str
    port: int
    secret_reference: str | None = None


def resolve_required_devices(env: Environment, values: dict) -> list[DeviceSpec]:
    settings = get_settings()
    meta = env.metadata_json or {}
    specs: list[DeviceSpec] = []

    for entry in meta.get("devices", []) or []:
        if not isinstance(entry, dict):
            continue
        role = entry.get("role")
        if not role:
            continue
        host = entry.get("host")
        if not host and entry.get("host_from_value"):
            host = values.get(entry["host_from_value"])
        # Simulated transport does not need a real host; fall back to the role.
        host = host or role
        specs.append(
            DeviceSpec(
                role=role,
                host=str(host),
                username=entry.get("username") or settings.ssh_default_username,
                port=int(entry.get("port", settings.ssh_port)),
                secret_reference=entry.get("secret_reference"),
            )
        )
    return specs
