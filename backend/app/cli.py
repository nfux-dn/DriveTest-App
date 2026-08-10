"""Small management CLI: seed definitions and generate a secret key.

Usage (inside the backend container):
    python -m app.cli seed
    python -m app.cli genkey
"""

from __future__ import annotations

import argparse
import logging

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.session import SessionLocal
from app.secrets.store import SecretStore
from app.suites.loader import load_suites
from app.suites.sync import SuiteSyncError, sync_suites

logger = logging.getLogger("drivetest.cli")


def cmd_seed() -> None:
    settings = get_settings()
    db = SessionLocal()
    try:
        if settings.definitions_source == "git":
            # Git single source of truth: index from the suites repo. Uses the
            # optional system token; best-effort (a private repo without a token
            # simply leaves the previously cached catalog in place).
            try:
                result = sync_suites(db, settings=settings)
                logger.info(
                    "seed_complete source=git suites=%d repo=%s commit=%s",
                    result.suites, result.repository, result.commit,
                )
            except SuiteSyncError as exc:
                logger.warning("seed_git_sync_failed: %s", exc)
        else:
            suites = load_suites(db, settings.definitions_path, prune=True)
            logger.info("seed_complete source=local suites=%d", suites)
    finally:
        db.close()


def cmd_genkey() -> None:
    print(SecretStore.generate_key())


def main() -> None:
    configure_logging()
    parser = argparse.ArgumentParser(description="DriveTest management CLI")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("seed", help="Index suite definitions into the database")
    sub.add_parser("genkey", help="Generate a Fernet key for DRIVETEST_SECRET_ENCRYPTION_KEY")
    args = parser.parse_args()

    if args.command == "seed":
        cmd_seed()
    elif args.command == "genkey":
        cmd_genkey()


if __name__ == "__main__":
    main()
