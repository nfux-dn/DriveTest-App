"""Per-user Git connection (spec sections 16-17, 28)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, created_at_column, uuid_str


class GitConnection(Base):
    __tablename__ = "git_connections"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid_str)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), index=True, nullable=False)
    provider: Mapped[str] = mapped_column(String, nullable=False, default="github")
    external_username: Mapped[str | None] = mapped_column(String, nullable=True)
    # Reference into SecretStore; NEVER the raw token (spec 17).
    secret_reference: Mapped[str] = mapped_column(String, nullable=False)
    scopes: Mapped[str | None] = mapped_column(String, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
