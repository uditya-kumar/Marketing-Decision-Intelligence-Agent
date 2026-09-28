"""FastAPI dependency providers: build services from a request-scoped session."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from mdia.db.session import get_session
from mdia.services.ingestion import IngestionService
from mdia.services.metrics import MetricsService
from mdia.services.settings import SettingsService

SessionDep = Annotated[Session, Depends(get_session)]


def get_ingestion_service(session: SessionDep) -> IngestionService:
    return IngestionService(session)


IngestionServiceDep = Annotated[IngestionService, Depends(get_ingestion_service)]


def get_settings_service(session: SessionDep) -> SettingsService:
    return SettingsService(session)


SettingsServiceDep = Annotated[SettingsService, Depends(get_settings_service)]


def get_metrics_service(session: SessionDep) -> MetricsService:
    return MetricsService(session)


MetricsServiceDep = Annotated[MetricsService, Depends(get_metrics_service)]
