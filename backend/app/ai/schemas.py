"""AI connection API schemas. The API key is never included in any response."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class AiConnectRequest(BaseModel):
    provider: str  # openai | anthropic
    api_key: str
    model: str | None = None


class AiConnectionOut(BaseModel):
    id: str
    provider: str
    model: str | None = None
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}
