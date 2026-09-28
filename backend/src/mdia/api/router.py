"""Aggregates the feature routers into the ``/api/v1`` router.

``/health`` is mounted at the application root instead (see ``main.py``).
"""

from __future__ import annotations

from fastapi import APIRouter

from mdia.api.routes import ingestion, metrics, settings, today, trust

api_router = APIRouter()
api_router.include_router(ingestion.router)
api_router.include_router(settings.router)
api_router.include_router(metrics.router)
api_router.include_router(today.router)
api_router.include_router(trust.router)
