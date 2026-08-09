"""Prerequisite instance model (spec sections 14, 28).

The template lives in Git/definitions; the instance stores the actual values a
user supplied for a specific run. Sensitive values are not stored directly.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import ValidationStatus
from app.db.base import Base, created_at_column, uuid_str


class PrerequisiteInstance(Base):
    __tablename__ = "prerequisite_instances"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid_str)
    run_id: Mapped[str] = mapped_column(String, ForeignKey("runs.id"), index=True, nullable=False)
    template_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    values_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    validation_status: Mapped[str] = mapped_column(
        String, nullable=False, default=ValidationStatus.PENDING.value
    )
    created_at: Mapped[datetime] = created_at_column()
