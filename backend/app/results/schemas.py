"""Result API schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.runs.schemas import TestRunOut

__all__ = ["TestRunOut", "ArtifactOut"]


class ArtifactOut(BaseModel):
    id: str
    artifact_type: str
    path_or_object_key: str
    size: int | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
