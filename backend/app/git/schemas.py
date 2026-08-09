"""Git API schemas. Tokens are never included in any response (spec 17)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ConnectPatRequest(BaseModel):
    """Connect using a GitHub personal access token (dev-friendly fallback)."""

    token: str


class GitConnectionOut(BaseModel):
    id: str
    provider: str
    external_username: str | None = None
    scopes: str | None = None
    expires_at: datetime | None = None

    model_config = {"from_attributes": True}


class RepositoryOut(BaseModel):
    id: int
    full_name: str
    name: str
    private: bool
    default_branch: str | None = None


class BranchOut(BaseModel):
    name: str
    commit_sha: str


class CommitOut(BaseModel):
    sha: str
    message: str
    author: str | None = None
    date: datetime | None = None
