"""Fetch an exact Git revision into a workspace (spec section 18).

Flow: clone the branch with the user's token, checkout the exact commit, record
the resolved SHA, then scrub the token from the remote URL so it never persists
in the workspace. The token is never logged.
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

from app.core.errors import ApiError
from app.git.validators import validate_full_name, validate_ref, validate_sha

logger = logging.getLogger("drivetest.git.fetch")

_GIT_TIMEOUT = 120


def _run_git(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
    # We never log args that may contain a token; callers control what is logged.
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        timeout=_GIT_TIMEOUT,
    )


def fetch_revision(
    repo_dir: Path,
    full_name: str,
    branch: str,
    token: str,
    commit: str | None = None,
) -> str:
    """Clone/checkout and return the resolved commit SHA."""
    full_name = validate_full_name(full_name)
    branch = validate_ref(branch)
    if commit:
        commit = validate_sha(commit)

    repo_dir.mkdir(parents=True, exist_ok=True)
    auth_url = f"https://x-access-token:{token}@github.com/{full_name}.git"
    clean_url = f"https://github.com/{full_name}.git"

    logger.info("git_clone repo=%s branch=%s", full_name, branch)
    result = _run_git(["clone", "--branch", branch, "--depth", "50", auth_url, str(repo_dir)])
    if result.returncode != 0:
        # Do not echo stderr verbatim (could contain the URL/token); log generically.
        logger.warning("git_clone_failed repo=%s branch=%s", full_name, branch)
        raise ApiError(code="GIT_FETCH_FAILED", message="Unable to fetch repository.", status_code=502)

    if commit:
        checkout = _run_git(["checkout", commit], cwd=repo_dir)
        if checkout.returncode != 0:
            raise ApiError(code="GIT_CHECKOUT_FAILED", message="Unable to checkout commit.", status_code=502)

    rev = _run_git(["rev-parse", "HEAD"], cwd=repo_dir)
    if rev.returncode != 0:
        raise ApiError(code="GIT_REVPARSE_FAILED", message="Unable to resolve commit SHA.", status_code=502)
    commit_sha = rev.stdout.strip()

    # Scrub the token from the workspace remote (spec 17: no tokens in stored URLs).
    _run_git(["remote", "set-url", "origin", clean_url], cwd=repo_dir)

    logger.info("git_fetched repo=%s commit=%s", full_name, commit_sha)
    return commit_sha
