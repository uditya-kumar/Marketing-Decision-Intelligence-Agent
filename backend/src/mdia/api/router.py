"""Aggregates the feature routers into the ``/api/v1`` router.

``/health`` is mounted at the application root instead (see ``main.py``).
"""

from __future__ import annotations

from fastapi import APIRouter

from mdia.api.routes import ingestion

api_router = APIRouter()
api_router.include_router(ingestion.router)
