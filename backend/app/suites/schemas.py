"""Suite API schemas."""

from __future__ import annotations

from pydantic import BaseModel


class SuiteOut(BaseModel):
    id: str
    name: str
    description: str | None = None
    tests: list[str] = []

    model_config = {"from_attributes": True}


class SuiteReadmeOut(BaseModel):
    """The suite's README markdown (purpose + connectivity), for the Environment tab."""

    suite_id: str
    markdown: str
