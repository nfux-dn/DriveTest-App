"""Canonical enums for the platform.

These are the single source of truth for status/verdict strings. The backend is
authoritative (spec section 41); the frontend only mirrors these values for
display and must never reimplement verdict logic.
"""

from __future__ import annotations

from enum import StrEnum


class ExecutionStatus(StrEnum):
    """How a test execution went, independent of the product result (spec 8)."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    SCRIPT_ERROR = "SCRIPT_ERROR"
    INFRA_ERROR = "INFRA_ERROR"
    TIMEOUT = "TIMEOUT"
    CANCELLED = "CANCELLED"
    SKIPPED = "SKIPPED"


class TestVerdict(StrEnum):
    """Deterministic verdict the test itself reports (spec 5). May also be null."""

    PASSED = "PASSED"
    FAILED = "FAILED"


class AiVerdict(StrEnum):
    """Verdict returned by the AI reviewer (spec 22)."""

    PASSED = "PASSED"
    FAILED = "FAILED"
    INCONCLUSIVE = "INCONCLUSIVE"


class FinalVerdict(StrEnum):
    """Computed final verdict (spec 7)."""

    PASSED = "PASSED"
    FAILED = "FAILED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


class RunStatus(StrEnum):
    """Overall status of a run (a suite execution)."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class ValidationStatus(StrEnum):
    """Whether a prerequisite instance passed validation."""

    PENDING = "PENDING"
    VALID = "VALID"
    INVALID = "INVALID"
