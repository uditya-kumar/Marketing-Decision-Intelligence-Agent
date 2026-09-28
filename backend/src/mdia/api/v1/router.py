"""Aggregates all v1 feature routers into a single API router.

Feature routes (settings, ingestion, today, ...) are added here in later phases.
``/health`` is mounted at the application root instead (see ``main.py``).
"""

from __future__ import annotations

from fastapi import APIRouter

api_router = APIRouter()
