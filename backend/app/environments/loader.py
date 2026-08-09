"""Load environment definitions from the definitions source (plan D8).

For MVP, environments are seeded from YAML files under definitions/environments/.
Admin CRUD is deferred.
"""

from __future__ import annotations

import logging
from pathlib import Path

import yaml
from sqlalchemy.orm import Session

from app.environments.models import Environment

logger = logging.getLogger("drivetest.environments.loader")


def load_environments(db: Session, definitions_dir: Path) -> int:
    env_root = definitions_dir / "environments"
    if not env_root.exists():
        logger.warning("environments_dir_missing path=%s", env_root)
        return 0

    count = 0
    for env_yaml in sorted(env_root.glob("*.yaml")):
        with env_yaml.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
        env_id = data.get("id") or data.get("name") or env_yaml.stem
        env = db.get(Environment, env_id)
        if env is None:
            env = Environment(id=env_id)
            db.add(env)
        env.name = data.get("name", env_id)
        env.platform = data.get("platform")
        env.system_type = data.get("system_type")
        env.software_version = str(data.get("software_version")) if data.get("software_version") else None
        env.capabilities_json = data.get("capabilities", []) or []
        env.metadata_json = data.get("metadata", {}) or {}
        env.enabled = bool(data.get("enabled", True))
        count += 1
        logger.info("environment_indexed id=%s platform=%s", env_id, env.platform)

    db.commit()
    return count
