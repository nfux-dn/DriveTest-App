"""Environment API schemas."""

from __future__ import annotations

from pydantic import BaseModel


class EnvironmentOut(BaseModel):
    id: str
    name: str
    platform: str | None = None
    system_type: str | None = None
    software_version: str | None = None
    capabilities: list[str] = []
    metadata: dict = {}
    enabled: bool = True

    model_config = {"from_attributes": True}


class CompatibilityResult(BaseModel):
    """Explains why an environment is or is not compatible with a suite."""

    environment: EnvironmentOut
    compatible: bool
    reasons: list[str] = []
