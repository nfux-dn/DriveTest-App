"""Suite API schemas."""

from __future__ import annotations

from pydantic import BaseModel


class SuiteRequirements(BaseModel):
    min_devices: int = 0
    traffic_generator: bool = False
    capabilities: list[str] = []


class SuiteOut(BaseModel):
    id: str
    name: str
    description: str | None = None
    requirements: SuiteRequirements
    supported_platforms: list[str] = []
    tests: list[str] = []

    model_config = {"from_attributes": True}
