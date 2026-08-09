"""GitHub OAuth web flow (spec section 17).

Optional in dev: if client id/secret are not configured, the start endpoint
returns a clear error and users connect with a PAT instead. Read-only scope.
"""

from __future__ import annotations

import logging
import secrets

import httpx

from app.core.config import get_settings
from app.core.errors import ApiError

logger = logging.getLogger("drivetest.git.oauth")

_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
_TOKEN_URL = "https://github.com/login/oauth/access_token"
# Read-only: no scope grants access only to public data + repo metadata the user
# can already see. 'repo' would be needed for private repos; keep minimal for MVP.
_SCOPE = "read:user"


def is_configured() -> bool:
    s = get_settings()
    return bool(s.github_client_id and s.github_client_secret)


def build_authorize_url() -> tuple[str, str]:
    if not is_configured():
        raise ApiError(
            code="OAUTH_NOT_CONFIGURED",
            message="GitHub OAuth is not configured. Connect with a personal access token instead.",
            status_code=400,
        )
    s = get_settings()
    state = secrets.token_urlsafe(24)
    params = {
        "client_id": s.github_client_id,
        "redirect_uri": s.github_oauth_callback,
        "scope": _SCOPE,
        "state": state,
    }
    query = "&".join(f"{k}={httpx.QueryParams({k: v})[k]}" for k, v in params.items())
    return f"{_AUTHORIZE_URL}?{query}", state


def exchange_code_for_token(code: str) -> str:
    s = get_settings()
    try:
        with httpx.Client(timeout=20.0) as client:
            resp = client.post(
                _TOKEN_URL,
                headers={"Accept": "application/json"},
                data={
                    "client_id": s.github_client_id,
                    "client_secret": s.github_client_secret,
                    "code": code,
                    "redirect_uri": s.github_oauth_callback,
                },
            )
    except httpx.HTTPError as exc:
        raise ApiError(code="OAUTH_EXCHANGE_FAILED", message="OAuth exchange failed.", status_code=502) from exc

    data = resp.json()
    token = data.get("access_token")
    if not token:
        raise ApiError(code="OAUTH_EXCHANGE_FAILED", message="OAuth did not return a token.", status_code=502)
    return token
