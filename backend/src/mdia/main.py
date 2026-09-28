"""FastAPI application factory and ASGI entrypoint.

Run with: ``uv run uvicorn mdia.main:app --reload``
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

import structlog
from fastapi import FastAPI

from mdia.api import errors
from mdia.api.router import api_router
from mdia.api.routes import health
from mdia.core.logging import configure_logging
from mdia.core.settings import get_settings

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

log = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Configure logging on startup; nothing to tear down yet."""
    settings = get_settings()
    configure_logging(settings.log_level)
    log.info("app.startup", env=settings.app_env, llm_provider=settings.llm_provider)
    yield
    log.info("app.shutdown")


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    app = FastAPI(
        title="MDIA API",
        version="0.1.0",
        description="Marketing Decision Intelligence Agent",
        lifespan=lifespan,
        responses=errors.RESPONSES,
    )
    errors.register(app)
    app.include_router(health.router)
    app.include_router(api_router, prefix="/api/v1")
    return app


app = create_app()
