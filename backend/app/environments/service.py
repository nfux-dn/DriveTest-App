"""Environment read services and compatibility resolution."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.environments.matcher import evaluate_compatibility
from app.environments.models import Environment
from app.environments.schemas import CompatibilityResult, EnvironmentOut
from app.suites.service import get_suite


def _to_out(env: Environment) -> EnvironmentOut:
    return EnvironmentOut(
        id=env.id,
        name=env.name,
        platform=env.platform,
        system_type=env.system_type,
        software_version=env.software_version,
        capabilities=env.capabilities_json or [],
        metadata=env.metadata_json or {},
        enabled=env.enabled,
    )


def list_environments(db: Session) -> list[EnvironmentOut]:
    envs = db.scalars(select(Environment).order_by(Environment.name)).all()
    return [_to_out(e) for e in envs]


def get_environment(db: Session, environment_id: str) -> Environment:
    env = db.get(Environment, environment_id)
    if env is None:
        raise ApiError(code="ENVIRONMENT_NOT_FOUND", message="Environment not found.", status_code=404)
    return env


def get_environment_out(db: Session, environment_id: str) -> EnvironmentOut:
    return _to_out(get_environment(db, environment_id))


def compatible_environments(db: Session, suite_id: str) -> list[CompatibilityResult]:
    """Return only environments compatible with the suite (spec Phase 2)."""
    suite = get_suite(db, suite_id)
    envs = db.scalars(select(Environment).order_by(Environment.name)).all()
    results: list[CompatibilityResult] = []
    for env in envs:
        compatible, reasons = evaluate_compatibility(suite, env)
        if compatible:
            results.append(CompatibilityResult(environment=_to_out(env), compatible=True, reasons=[]))
    return results
