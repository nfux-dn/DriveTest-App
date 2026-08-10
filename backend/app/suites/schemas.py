"""Suite API schemas."""

from __future__ import annotations

from pydantic import BaseModel


class SuiteOut(BaseModel):
    id: str
    name: str
    description: str | None = None
    tests: list[str] = []
    # Provenance so the UI can show where a suite came from.
    source_repository: str | None = None
    source_branch: str | None = None
    indexed_commit: str | None = None

    model_config = {"from_attributes": True}


class SuiteReadmeOut(BaseModel):
    """The suite's README markdown (purpose + connectivity), for the Environment tab."""

    suite_id: str
    markdown: str


class SuiteSyncOut(BaseModel):
    """Result of re-indexing the suite catalog from the suites Git repository."""

    suites: int
    repository: str
    branch: str
    commit: str
