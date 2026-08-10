"""FastAPI application factory (spec sections 24, 26).

Modular monolith: one app, many domain routers. This file wires middleware,
error handlers, and routers together and exposes a health endpoint.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.core.config import get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import RequestIdMiddleware, configure_logging

logger = logging.getLogger("drivetest")

health_router = APIRouter(tags=["health"])


@health_router.get("/health")
def health() -> dict[str, str]:
    """Liveness endpoint used by the frontend and orchestration (spec Phase 1)."""
    return {"status": "ok"}


def _include_routers(app: FastAPI) -> None:
    from app.auth.router import router as auth_router
    from app.git.router import router as git_router
    from app.prerequisites.router import router as prerequisites_router
    from app.results.router import router as results_router
    from app.runs.router import router as runs_router
    from app.suites.router import router as suites_router

    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(suites_router)
    app.include_router(prerequisites_router)
    app.include_router(git_router)
    app.include_router(runs_router)
    app.include_router(results_router)


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging()

    app = FastAPI(title="DriveTest Orchestration Platform", version="0.1.0")

    # Signed-cookie session for the simple dev auth (spec section 30).
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.session_secret,
        same_site="lax",
        https_only=False,
    )
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)
    _include_routers(app)

    logger.info("app_started environment=%s", settings.environment)
    return app


app = create_app()
