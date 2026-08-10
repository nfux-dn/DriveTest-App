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

logger = logging.getLogger("drivetest.cli")


def cmd_seed() -> None:
    settings = get_settings()
    db = SessionLocal()
    try:
        suites = load_suites(db, settings.definitions_path)
        logger.info("seed_complete suites=%d", suites)
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
