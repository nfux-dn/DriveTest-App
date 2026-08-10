"""Run model (spec sections 18, 28). A Run is one execution of a Suite."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import RunStatus
from app.db.base import Base, created_at_column, uuid_str


class Run(Base):
    __tablename__ = "runs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid_str)
    suite_id: Mapped[str] = mapped_column(String, ForeignKey("suites.id"), nullable=False)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False)
    repository: Mapped[str | None] = mapped_column(String, nullable=True)
    branch: Mapped[str | None] = mapped_column(String, nullable=True)
    commit_sha: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default=RunStatus.PENDING.value)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = created_at_column()
