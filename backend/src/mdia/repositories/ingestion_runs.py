"""Ingestion run log."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select

from mdia.models import IngestionRun

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sqlalchemy.orm import Session


class IngestionRunRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, run: IngestionRun) -> IngestionRun:
        self._session.add(run)
        self._session.flush()
        return run

    def list_recent(self, limit: int) -> Sequence[IngestionRun]:
        stmt = select(IngestionRun).order_by(IngestionRun.id.desc()).limit(limit)
        return self._session.scalars(stmt).all()
