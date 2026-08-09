"""Git connection services: connect per-user, list repos/branches/commits.

The token is stored encrypted via SecretStore; only its reference lives on the
git_connections row. When we need the token we reveal it locally and pass it to
the GitHub client, never to the frontend or logs (spec sections 16-17, 37).
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.git.github import GitHubClient
from app.git.models import GitConnection
from app.git.schemas import BranchOut, CommitOut, GitConnectionOut, RepositoryOut
from app.secrets.store import SecretStore


def get_connection(db: Session, user_id: str) -> GitConnection | None:
    return db.scalar(
        select(GitConnection).where(GitConnection.user_id == user_id, GitConnection.provider == "github")
    )


def require_connection(db: Session, user_id: str) -> GitConnection:
    conn = get_connection(db, user_id)
    if conn is None:
        raise ApiError(code="GIT_NOT_CONNECTED", message="No GitHub connection for this user.", status_code=400)
    return conn


def connect_with_pat(db: Session, user_id: str, token: str) -> GitConnectionOut:
    # Validate the token by fetching the authenticated user before storing it.
    client = GitHubClient(token)
    gh_user = client.get_authenticated_user()

    store = SecretStore(db)
    conn = get_connection(db, user_id)
    if conn is not None and conn.secret_reference:
        store.delete(conn.secret_reference)
    secret_reference = store.store(token)

    if conn is None:
        conn = GitConnection(user_id=user_id, provider="github")
        db.add(conn)
    conn.secret_reference = secret_reference
    conn.external_username = gh_user.get("login")
    conn.scopes = "read-only"
    conn.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(conn)
    return GitConnectionOut.model_validate(conn)


def _client_for(db: Session, user_id: str) -> GitHubClient:
    conn = require_connection(db, user_id)
    token = SecretStore(db).reveal(conn.secret_reference)
    return GitHubClient(token)


def list_connections(db: Session, user_id: str) -> list[GitConnectionOut]:
    conn = get_connection(db, user_id)
    return [GitConnectionOut.model_validate(conn)] if conn else []


def list_repositories(db: Session, user_id: str) -> list[RepositoryOut]:
    return _client_for(db, user_id).list_repositories()


def list_branches(db: Session, user_id: str, full_name: str) -> list[BranchOut]:
    return _client_for(db, user_id).list_branches(full_name)


def list_commits(db: Session, user_id: str, full_name: str, branch: str | None) -> list[CommitOut]:
    return _client_for(db, user_id).list_commits(full_name, sha=branch)


def reveal_token(db: Session, user_id: str) -> str:
    """Backend-only: used by the runner to fetch the repo. Never exposed via API."""
    conn = require_connection(db, user_id)
    return SecretStore(db).reveal(conn.secret_reference)
