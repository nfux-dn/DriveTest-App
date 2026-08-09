"""Thin GitHub REST client using the *user's own* token (spec sections 16-17).

Only read operations are used. The token is passed in per request and never
logged. This client is intentionally small; a different provider would implement
the same method surface behind a shared abstraction later.
"""

from __future__ import annotations

import logging

import httpx

from app.core.errors import ApiError
from app.git.schemas import BranchOut, CommitOut, RepositoryOut

logger = logging.getLogger("drivetest.git.github")

_API_BASE = "https://api.github.com"
_TIMEOUT = 20.0


class GitHubClient:
    def __init__(self, token: str) -> None:
        self._token = token

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def _get(self, path: str, params: dict | None = None) -> httpx.Response:
        try:
            with httpx.Client(base_url=_API_BASE, timeout=_TIMEOUT) as client:
                resp = client.get(path, headers=self._headers(), params=params)
        except httpx.HTTPError as exc:
            logger.warning("github_request_error path=%s", path)
            raise ApiError(code="GIT_REQUEST_FAILED", message="GitHub request failed.", status_code=502) from exc
        if resp.status_code == 401:
            raise ApiError(code="GIT_UNAUTHORIZED", message="GitHub token is invalid or expired.", status_code=401)
        if resp.status_code == 403:
            raise ApiError(code="GIT_FORBIDDEN", message="GitHub denied access.", status_code=403)
        if resp.status_code >= 400:
            raise ApiError(
                code="GIT_REQUEST_FAILED",
                message="GitHub request failed.",
                status_code=502,
                details={"status": resp.status_code},
            )
        return resp

    def get_authenticated_user(self) -> dict:
        return self._get("/user").json()

    def list_repositories(self, per_page: int = 50) -> list[RepositoryOut]:
        resp = self._get(
            "/user/repos",
            params={"per_page": per_page, "sort": "updated", "affiliation": "owner,collaborator,organization_member"},
        )
        return [
            RepositoryOut(
                id=r["id"],
                full_name=r["full_name"],
                name=r["name"],
                private=r["private"],
                default_branch=r.get("default_branch"),
            )
            for r in resp.json()
        ]

    def list_branches(self, full_name: str, per_page: int = 100) -> list[BranchOut]:
        resp = self._get(f"/repos/{full_name}/branches", params={"per_page": per_page})
        return [BranchOut(name=b["name"], commit_sha=b["commit"]["sha"]) for b in resp.json()]

    def list_commits(self, full_name: str, sha: str | None = None, per_page: int = 30) -> list[CommitOut]:
        params: dict = {"per_page": per_page}
        if sha:
            params["sha"] = sha
        resp = self._get(f"/repos/{full_name}/commits", params=params)
        commits: list[CommitOut] = []
        for c in resp.json():
            commit = c.get("commit", {})
            author = commit.get("author", {}) or {}
            commits.append(
                CommitOut(
                    sha=c["sha"],
                    message=(commit.get("message") or "").split("\n")[0],
                    author=author.get("name"),
                    date=author.get("date"),
                )
            )
        return commits
