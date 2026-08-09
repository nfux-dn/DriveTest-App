"""Per-run isolated workspace management (spec section 18)."""

from __future__ import annotations

import logging
import shutil
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger("drivetest.runner.workspace")


@dataclass
class Workspace:
    root: Path
    repo: Path
    results: Path
    logs: Path
    artifacts: Path


def create_workspace(workspaces_dir: Path, run_id: str) -> Workspace:
    root = workspaces_dir / run_id
    ws = Workspace(
        root=root,
        repo=root / "repo",
        results=root / "results",
        logs=root / "logs",
        artifacts=root / "artifacts",
    )
    for path in (ws.repo, ws.results, ws.logs, ws.artifacts):
        path.mkdir(parents=True, exist_ok=True)
    logger.info("workspace_created run_id=%s root=%s", run_id, root)
    return ws


def cleanup_workspace(workspaces_dir: Path, run_id: str) -> None:
    root = workspaces_dir / run_id
    if root.exists():
        shutil.rmtree(root, ignore_errors=True)
        logger.info("workspace_removed run_id=%s", run_id)
