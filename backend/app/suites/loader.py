"""Load suite definitions from the definitions source into the database.

Plan open-decision D5: the definitions source is indexed into the DB so users
can browse suites before selecting a Git revision. For MVP the local
`definitions/` directory is that source.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

import yaml
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.runs.models import Run
from app.suites.models import Suite

logger = logging.getLogger("drivetest.suites.loader")


def _read_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Suite file {path} must contain a mapping.")
    return data


def load_suites(
    db: Session,
    definitions_dir: Path,
    *,
    repository: str | None = None,
    branch: str | None = None,
    commit: str | None = None,
    prune: bool = True,
) -> int:
    """Index all suites under definitions_dir/suites/*/prerequisites.yaml.

    Each suite has one merged file (suite definition + prerequisite form); this
    reads the suite definition part (id/name/description/tests) and records where
    it came from (repository/branch/commit). When `prune` is set, suites that are
    no longer present on disk are removed so the catalog matches the source.

    Returns the number of suites indexed.
    """
    suites_root = definitions_dir / "suites"
    if not suites_root.exists():
        logger.warning("suites_dir_missing path=%s", suites_root)
        return 0

    now = datetime.now(timezone.utc)
    seen: set[str] = set()
    count = 0
    for suite_file in sorted(suites_root.glob("*/prerequisites.yaml")):
        data = _read_yaml(suite_file)
        suite_id = data.get("id") or suite_file.parent.name
        seen.add(suite_id)
        suite = db.get(Suite, suite_id)
        if suite is None:
            suite = Suite(id=suite_id)
            db.add(suite)
        suite.name = data.get("name", suite_id)
        suite.description = data.get("description")
        suite.source_repository = repository
        suite.source_branch = branch
        suite.source_path = str(suite_file.parent.relative_to(definitions_dir))
        suite.indexed_commit = commit
        suite.indexed_at = now
        suite.archived = False  # in case a previously-archived suite returned
        suite.requirements_json = {}
        suite.supported_platforms_json = []
        suite.tests_json = data.get("tests", []) or []
        count += 1
        logger.info("suite_indexed id=%s tests=%d", suite_id, len(suite.tests_json))

    if prune:
        for suite in db.scalars(select(Suite)).all():
            if suite.id in seen:
                continue
            # A suite that's gone from the source but still has run history can't be
            # deleted (FK from runs); archive it so it's hidden but history survives.
            has_runs = db.scalar(select(func.count()).select_from(Run).where(Run.suite_id == suite.id))
            if has_runs:
                if not suite.archived:
                    logger.info("suite_archived id=%s (gone from source, has runs)", suite.id)
                suite.archived = True
            else:
                logger.info("suite_pruned id=%s (no longer in source)", suite.id)
                db.delete(suite)

    db.commit()
    return count
