"""Suite model (spec section 10, 28).

Suites are indexed from the definitions source. The requirements, supported
platforms, and ordered test list are stored as JSON so the matcher and runner
can use them without re-reading YAML (plan schema additions D9).
"""

from __future__ import annotations

from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Suite(Base):
    __tablename__ = "suites"

    # We use the suite's own id (e.g. "pwhe_shaping") as the primary key.
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    source_repository: Mapped[str | None] = mapped_column(String, nullable=True)
    source_path: Mapped[str | None] = mapped_column(String, nullable=True)
    requirements_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    supported_platforms_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    tests_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
