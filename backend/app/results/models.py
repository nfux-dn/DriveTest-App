"""Result-related models: test_runs, ai_evaluations, artifacts (spec section 28).

test_verdict, ai_verdict and final_verdict are stored as separate columns so
disagreement is never hidden (spec sections 5-8, 35). In milestones 1-5 the
runner fills execution_status, test_verdict and result_json; ai_verdict and
final_verdict are populated in later phases (7-8).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import ExecutionStatus
from app.db.base import Base, created_at_column, uuid_str


class TestRun(Base):
    __tablename__ = "test_runs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid_str)
    run_id: Mapped[str] = mapped_column(String, ForeignKey("runs.id"), index=True, nullable=False)
    test_id: Mapped[str] = mapped_column(String, nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    execution_status: Mapped[str] = mapped_column(
        String, nullable=False, default=ExecutionStatus.PENDING.value
    )
    test_verdict: Mapped[str | None] = mapped_column(String, nullable=True)
    ai_verdict: Mapped[str | None] = mapped_column(String, nullable=True)
    final_verdict: Mapped[str | None] = mapped_column(String, nullable=True)
    ai_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    result_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = created_at_column()


class AiEvaluation(Base):
    __tablename__ = "ai_evaluations"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid_str)
    test_run_id: Mapped[str] = mapped_column(String, ForeignKey("test_runs.id"), index=True, nullable=False)
    model: Mapped[str] = mapped_column(String, nullable=False)
    prompt_version: Mapped[str] = mapped_column(String, nullable=False)
    policy_version: Mapped[str] = mapped_column(String, nullable=False)
    ai_verdict: Mapped[str] = mapped_column(String, nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    summary: Mapped[str | None] = mapped_column(String, nullable=True)
    analysis_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = created_at_column()


class Artifact(Base):
    __tablename__ = "artifacts"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid_str)
    test_run_id: Mapped[str] = mapped_column(String, ForeignKey("test_runs.id"), index=True, nullable=False)
    artifact_type: Mapped[str] = mapped_column(String, nullable=False)
    path_or_object_key: Mapped[str] = mapped_column(String, nullable=False)
    size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = created_at_column()
