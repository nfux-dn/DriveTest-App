"""Suite model (spec section 10, 28).

Suites are indexed from the definitions source. The requirements, supported
platforms, and ordered test list are stored as JSON so the matcher and runner
can use them without re-reading YAML (plan schema additions D9).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Suite(Base):
    __tablename__ = "suites"

    # We use the suite's own id (e.g. "pwhe_shaping") as the primary key.
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    # Provenance: which repo/branch/commit this suite was indexed from.
    source_repository: Mapped[str | None] = mapped_column(String, nullable=True)
    source_branch: Mapped[str | None] = mapped_column(String, nullable=True)
    source_path: Mapped[str | None] = mapped_column(String, nullable=True)
    indexed_commit: Mapped[str | None] = mapped_column(String, nullable=True)
    indexed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # A suite that vanished from the source but still has run history is archived
    # (hidden from the catalog) rather than deleted, to preserve that history.
    archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    requirements_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    supported_platforms_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    tests_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
