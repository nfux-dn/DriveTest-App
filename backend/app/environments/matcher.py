"""Requirements matcher (spec sections 3, 10, Phase 2).

Answers: "Can this Environment run this Suite at all?" Compatibility is based on
device count, traffic generator, required capabilities, and supported platforms.
The reasons list makes the decision transparent in the UI.
"""

from __future__ import annotations

from app.environments.models import Environment
from app.suites.models import Suite


def evaluate_compatibility(suite: Suite, env: Environment) -> tuple[bool, list[str]]:
    """Return (compatible, reasons). Reasons explain any incompatibility."""
    reasons: list[str] = []
    reqs = suite.requirements_json or {}

    if not env.enabled:
        reasons.append("Environment is disabled.")

    # Platform support: if the suite lists supported platforms, the env must match.
    supported_platforms = suite.supported_platforms_json or []
    if supported_platforms and env.platform not in supported_platforms:
        reasons.append(
            f"Platform '{env.platform}' is not in supported platforms {supported_platforms}."
        )

    # Minimum device count (device list lives in environment metadata).
    min_devices = int(reqs.get("min_devices", 0) or 0)
    device_count = _device_count(env)
    if device_count < min_devices:
        reasons.append(f"Requires at least {min_devices} devices, environment has {device_count}.")

    # Traffic generator requirement.
    if reqs.get("traffic_generator"):
        if not _has_traffic_generator(env):
            reasons.append("Requires a traffic generator, environment has none.")

    # Required capabilities must all be present.
    required_caps = set(reqs.get("capabilities", []) or [])
    env_caps = set(env.capabilities_json or [])
    missing = sorted(required_caps - env_caps)
    if missing:
        reasons.append(f"Missing required capabilities: {missing}.")

    return (len(reasons) == 0, reasons)


def _device_count(env: Environment) -> int:
    meta = env.metadata_json or {}
    devices = meta.get("devices")
    if isinstance(devices, list):
        return len(devices)
    if isinstance(devices, int):
        return devices
    return 0


def _has_traffic_generator(env: Environment) -> bool:
    meta = env.metadata_json or {}
    if meta.get("traffic_generator"):
        return True
    return "traffic_generator" in set(env.capabilities_json or [])
