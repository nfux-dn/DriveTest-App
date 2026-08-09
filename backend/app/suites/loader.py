"""Load suite definitions from the definitions source into the database.

Plan open-decision D5: the definitions source is indexed into the DB so users
can browse suites before selecting a Git revision. For MVP the local
`definitions/` directory is that source.
"""

from __future__ import annotations

import logging
from pathlib import Path

import yaml
from sqlalchemy.orm import Session

from app.suites.models import Suite

logger = logging.getLogger("drivetest.suites.loader")


def _read_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Suite file {path} must contain a mapping.")
    return data


def load_suites(db: Session, definitions_dir: Path) -> int:
    """Upsert all suites found under definitions_dir/suites/*/suite.yaml.

    Returns the number of suites indexed.
    """
    suites_root = definitions_dir / "suites"
    if not suites_root.exists():
        logger.warning("suites_dir_missing path=%s", suites_root)
        return 0

    count = 0
    for suite_yaml in sorted(suites_root.glob("*/suite.yaml")):
        data = _read_yaml(suite_yaml)
        suite_id = data.get("id") or suite_yaml.parent.name
        requirements = data.get("requirements", {}) or {}
        suite = db.get(Suite, suite_id)
        if suite is None:
            suite = Suite(id=suite_id)
            db.add(suite)
        suite.name = data.get("name", suite_id)
        suite.description = data.get("description")
        suite.source_path = str(suite_yaml.parent.relative_to(definitions_dir))
        suite.requirements_json = requirements
        suite.supported_platforms_json = data.get("supported_platforms", []) or []
        suite.tests_json = data.get("tests", []) or []
        count += 1
        logger.info("suite_indexed id=%s tests=%d", suite_id, len(suite.tests_json))

    db.commit()
    return count
