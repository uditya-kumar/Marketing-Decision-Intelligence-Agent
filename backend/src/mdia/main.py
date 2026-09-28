"""FastAPI application factory and ASGI entrypoint.

Run with: ``uv run uvicorn mdia.main:app --reload``
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

import structlog
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from mdia.api.v1.router import api_router
from mdia.api.v1.routes import health
from mdia.core.errors import MdiaError, NotFoundError, ValidationError
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


def _register_error_handlers(app: FastAPI) -> None:
    """Map domain errors to HTTP responses in one place (routes never do this)."""

    @app.exception_handler(NotFoundError)
    async def _not_found(_: Request, exc: NotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(ValidationError)
    async def _validation(_: Request, exc: ValidationError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    @app.exception_handler(MdiaError)
    async def _domain(_: Request, exc: MdiaError) -> JSONResponse:
        log.error("domain.error", error=str(exc), kind=type(exc).__name__)
        return JSONResponse(status_code=500, content={"detail": str(exc)})


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    app = FastAPI(
        title="MDIA API",
        version="0.1.0",
        description="Marketing Decision Intelligence Agent",
        lifespan=lifespan,
    )
    _register_error_handlers(app)
    app.include_router(health.router)
    app.include_router(api_router, prefix="/api/v1")
    return app


app = create_app()
