"""Health check route: reports database connectivity and the configured LLM provider."""

from __future__ import annotations

from typing import Literal

import structlog
from fastapi import APIRouter

from mdia.core.settings import get_settings
from mdia.db.session import check_database
from mdia.schemas.health import HealthResponse

log = structlog.get_logger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Return service health. Always 200; ``status`` is ``degraded`` if the DB is down."""
    settings = get_settings()

    database: Literal["ok", "unavailable"]
    try:
        check_database()
        database = "ok"
    except Exception as exc:
        log.warning("health.database_unavailable", error=str(exc))
        database = "unavailable"

    return HealthResponse(
        status="ok" if database == "ok" else "degraded",
        database=database,
        llm_provider=settings.llm_provider,
    )
