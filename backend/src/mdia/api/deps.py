"""FastAPI dependency providers: build services from a request-scoped session."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from mdia.db.session import get_session
from mdia.services.ingestion import IngestionService

SessionDep = Annotated[Session, Depends(get_session)]


def get_ingestion_service(session: SessionDep) -> IngestionService:
    return IngestionService(session)


IngestionServiceDep = Annotated[IngestionService, Depends(get_ingestion_service)]
