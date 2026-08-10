"""Per-user AI provider connection (mirrors git_connections, spec sections 17/37).

Each user connects their own AI provider; the API key is stored encrypted at rest
via SecretStore and referenced only by an opaque secret_reference. The key is
never returned to the frontend, logged, or placed in prompts.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, created_at_column, uuid_str


class AiConnection(Base):
    __tablename__ = "ai_connections"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid_str)
    user_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.id"), unique=True, index=True, nullable=False
    )
    provider: Mapped[str] = mapped_column(String, nullable=False)  # openai | anthropic
    secret_reference: Mapped[str] = mapped_column(String, nullable=False)
    model: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
