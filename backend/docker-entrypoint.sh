#!/usr/bin/env bash
set -euo pipefail

echo "[entrypoint] waiting for database..."
python - <<'PY'
import time
import sqlalchemy
from app.core.config import get_settings

url = get_settings().database_url
for attempt in range(30):
    try:
        engine = sqlalchemy.create_engine(url)
        with engine.connect() as conn:
            conn.execute(sqlalchemy.text("SELECT 1"))
        print("[entrypoint] database is ready")
        break
    except Exception as exc:  # noqa: BLE001
        print(f"[entrypoint] db not ready ({attempt+1}/30): {exc.__class__.__name__}")
        time.sleep(2)
else:
    raise SystemExit("[entrypoint] database did not become ready")
PY

echo "[entrypoint] running migrations..."
alembic upgrade head

echo "[entrypoint] seeding definitions..."
python -m app.cli seed || echo "[entrypoint] seed skipped/failed (continuing)"

echo "[entrypoint] starting API..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
