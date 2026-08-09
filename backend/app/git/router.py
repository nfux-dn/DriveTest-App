"""Git routes (spec section 29). Per-user identity; tokens never returned."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.auth.models import User
from app.db.session import get_db
from app.git import oauth, service
from app.git.schemas import (
    BranchOut,
    CommitOut,
    ConnectPatRequest,
    GitConnectionOut,
    RepositoryOut,
)
from app.git.validators import validate_full_name

router = APIRouter(prefix="/api/git", tags=["git"])


@router.get("/connections", response_model=list[GitConnectionOut])
def list_connections(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[GitConnectionOut]:
    return service.list_connections(db, user.id)


@router.post("/connect", response_model=GitConnectionOut)
def connect_pat(
    payload: ConnectPatRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> GitConnectionOut:
    return service.connect_with_pat(db, user.id, payload.token)


@router.get("/oauth/start")
def oauth_start(request: Request, user: User = Depends(get_current_user)) -> RedirectResponse:
    url, state = oauth.build_authorize_url()
    request.session["git_oauth_state"] = state
    return RedirectResponse(url)


@router.get("/oauth/callback")
def oauth_callback(
    code: str,
    state: str,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> GitConnectionOut:
    expected = request.session.get("git_oauth_state")
    if not expected or state != expected:
        from app.core.errors import ApiError

        raise ApiError(code="OAUTH_STATE_MISMATCH", message="OAuth state mismatch.", status_code=400)
    token = oauth.exchange_code_for_token(code)
    request.session.pop("git_oauth_state", None)
    return service.connect_with_pat(db, user.id, token)


@router.get("/repositories", response_model=list[RepositoryOut])
def list_repositories(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[RepositoryOut]:
    return service.list_repositories(db, user.id)


@router.get("/repositories/{full_name:path}/branches", response_model=list[BranchOut])
def list_branches(
    full_name: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[BranchOut]:
    return service.list_branches(db, user.id, validate_full_name(full_name))


@router.get("/repositories/{full_name:path}/commits", response_model=list[CommitOut])
def list_commits(
    full_name: str,
    branch: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[CommitOut]:
    return service.list_commits(db, user.id, validate_full_name(full_name), branch)
