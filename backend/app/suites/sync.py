"""Index the suite catalog from the suites Git repository (single source of truth).

In "git" mode the catalog you browse and the code that runs come from the same
repo. This module clones the configured suites repository at the configured
branch into a local cache, resolves the exact commit, then indexes the suites
(README + prerequisite form are read from this cache; runs fetch their own copy
at launch, pinned to a resolved commit).
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.git.validators import validate_full_name, validate_ref
from app.suites.loader import load_suites

logger = logging.getLogger("drivetest.suites.sync")

_GIT_TIMEOUT = 120


class SuiteSyncError(Exception):
    """Raised when the suites repository cannot be indexed."""


@dataclass
class SyncResult:
    suites: int
    repository: str
    branch: str
    commit: str


def _run_git(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        timeout=_GIT_TIMEOUT,
    )


def _clone(repository: str, branch: str, token: str | None, dest: Path) -> str:
    """Fresh, shallow clone of repository@branch into dest. Returns the commit SHA."""
    repository = validate_full_name(repository)
    branch = validate_ref(branch)

    # Always start clean so removed suites/files never linger in the cache.
    if dest.exists():
        shutil.rmtree(dest, ignore_errors=True)
    dest.mkdir(parents=True, exist_ok=True)

    if token:
        url = f"https://x-access-token:{token}@github.com/{repository}.git"
    else:
        url = f"https://github.com/{repository}.git"
    clean_url = f"https://github.com/{repository}.git"

    logger.info("suites_clone repo=%s branch=%s", repository, branch)
    result = _run_git(["clone", "--branch", branch, "--depth", "1", url, str(dest)])
    if result.returncode != 0:
        # Never echo stderr verbatim (may contain the token in the URL).
        logger.warning("suites_clone_failed repo=%s branch=%s", repository, branch)
        raise SuiteSyncError(
            f"Unable to clone suites repository '{repository}@{branch}'. "
            "Check the repository/branch and that a token with access is available."
        )

    rev = _run_git(["rev-parse", "HEAD"], cwd=dest)
    commit = rev.stdout.strip() if rev.returncode == 0 else ""
    # Scrub any token from the stored remote.
    _run_git(["remote", "set-url", "origin", clean_url], cwd=dest)
    logger.info("suites_cloned repo=%s commit=%s", repository, commit)
    return commit


def sync_suites(db: Session, token: str | None = None, settings: Settings | None = None) -> SyncResult:
    """Clone the suites repo at the configured branch and (re)index the catalog.

    `token` is optional: pass a user's GitHub token (or rely on the configured
    system token) for a private repo; omit for a public one.
    """
    settings = settings or get_settings()
    repository = settings.suites_repository
    branch = settings.suites_branch
    effective_token = token or settings.suites_git_token or None

    dest = settings.suites_cache_path
    commit = _clone(repository, branch, effective_token, dest)
    count = load_suites(
        db,
        dest,
        repository=repository,
        branch=branch,
        commit=commit,
        prune=True,
    )
    return SyncResult(suites=count, repository=repository, branch=branch, commit=commit)
