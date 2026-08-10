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

    # AI evaluator (spec sections 6, 21-23). Provider is pluggable; "mock" is the
    # offline default so dev/demo works without network or API keys.
    ai_provider: str = "mock"  # mock | openai | anthropic
    ai_max_retries: int = 2
    ai_request_timeout_seconds: float = 60.0
    # Max bytes of stdout/stderr excerpt included in an AI request (spec 21).
    ai_max_log_excerpt_bytes: int = 8000

    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_base_url: str = "https://api.openai.com/v1"

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-3-5-sonnet-latest"
    anthropic_base_url: str = "https://api.anthropic.com/v1"

    # Cursor (via the cursor-agent CLI). Key is a Cursor user/service API key.
    # cursor_model is optional; empty means let the CLI pick its default model.
    cursor_api_key: str = ""
    cursor_model: str = ""
    # Cursor agent runs are slower than a plain chat call; give them their own,
    # larger timeout (seconds).
    cursor_timeout_seconds: float = 120.0

    # SSH / device connections (spec section 51). Connections are owned by the Run
    # and reused by all tests; tests never open SSH themselves.
    ssh_transport: str = "simulated"  # simulated | ssh (paramiko)
    ssh_default_username: str = "admin"
    # Fallback SSH password used when a device field has no credential_ref
    # (e.g. a common lab login like DNOS dnroot). Empty means key/no-password.
    ssh_default_password: str = ""
    ssh_port: int = 22
    ssh_connect_timeout_seconds: float = 15.0
    ssh_command_timeout_seconds: float = 30.0
    ssh_reconnect_attempts: int = 2  # bounded reconnect policy
    # Directory containing the `drivetest` ExecutionContext SDK injected onto the
    # test subprocess PYTHONPATH.
    sdk_dir: str = "/app/sdk"

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
