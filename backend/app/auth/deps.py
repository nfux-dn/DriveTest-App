"""Authentication dependency: resolve the current user from the session cookie.

This is intentionally simple (spec section 30). The session middleware stores
the user id in a signed cookie; SSO can replace this later without touching the
rest of the app, since routes depend only on `get_current_user`.
"""

from __future__ import annotations

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.auth.models import User
from app.auth.service import get_user
from app.core.errors import ApiError
from app.db.session import get_db


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    user_id = request.session.get("user_id")
    if not user_id:
        raise ApiError(code="NOT_AUTHENTICATED", message="Authentication required.", status_code=401)
    user = get_user(db, user_id)
    if user is None:
        request.session.clear()
        raise ApiError(code="NOT_AUTHENTICATED", message="Session user no longer exists.", status_code=401)
    return user
