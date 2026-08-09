"""Application configuration.

All settings are read from environment variables (see .env.example). We keep a
single Settings object so the rest of the code never reads os.environ directly.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DRIVETEST_", env_file=".env", extra="ignore")

    # General
    environment: str = "development"
    debug: bool = True

    # Database (sync SQLAlchemy + psycopg3 driver)
    database_url: str = "postgresql+psycopg://drivetest:drivetest@db:5432/drivetest"

    # Session cookie signing key. MUST be overridden in production.
    session_secret: str = "dev-insecure-session-secret-change-me"

    # Fernet key for SecretStore encryption. Base64 urlsafe 32-byte key.
    # If empty, SecretStore raises when asked to store a secret.
    secret_encryption_key: str = ""

    # CORS: comma-separated list of allowed frontend origins.
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Where suite/environment/prerequisite definitions are loaded from (dev seed).
    # See plan open-decision D5.
    definitions_dir: str = "/app/definitions"

    # Root directory for per-run isolated workspaces (spec section 18).
    workspaces_dir: str = "/tmp/drivetest-workspaces"

    # Runner limits (spec section 19, open-decision D7).
    test_timeout_seconds: int = 300
    max_capture_bytes: int = 2_000_000  # per stream (stdout/stderr)

    # GitHub OAuth (optional in dev; PAT fallback is used when unset).
    github_client_id: str = ""
    github_client_secret: str = ""
    github_oauth_callback: str = "http://localhost:8000/api/git/oauth/callback"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def definitions_path(self) -> Path:
        return Path(self.definitions_dir)

    @property
    def workspaces_path(self) -> Path:
        return Path(self.workspaces_dir)


@lru_cache
def get_settings() -> Settings:
    return Settings()
