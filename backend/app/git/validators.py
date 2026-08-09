"""Validate Git-related user input to prevent injection/traversal (spec 37)."""

from __future__ import annotations

import re

from app.core.errors import ApiError

_FULL_NAME_RE = re.compile(r"^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$")
_REF_RE = re.compile(r"^[A-Za-z0-9._/-]+$")
_SHA_RE = re.compile(r"^[0-9a-fA-F]{7,40}$")


def validate_full_name(full_name: str) -> str:
    if not _FULL_NAME_RE.match(full_name) or ".." in full_name:
        raise ApiError(code="INVALID_REPOSITORY", message="Invalid repository name.", status_code=400)
    return full_name


def validate_ref(ref: str) -> str:
    if not _REF_RE.match(ref) or ".." in ref:
        raise ApiError(code="INVALID_REF", message="Invalid branch/ref name.", status_code=400)
    return ref


def validate_sha(sha: str) -> str:
    if not _SHA_RE.match(sha):
        raise ApiError(code="INVALID_COMMIT", message="Invalid commit SHA.", status_code=400)
    return sha
