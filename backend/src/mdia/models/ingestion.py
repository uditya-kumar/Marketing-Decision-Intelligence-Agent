"""Ingestion run log: one row per uploaded file."""

from __future__ import annotations

import datetime as dt
from typing import Any, Literal, get_args

from sqlalchemy import CheckConstraint, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from mdia.db.base import Base

RunStatus = Literal["success", "partial", "failed"]
_STATUSES = ", ".join(f"'{status}'" for status in get_args(RunStatus))


class IngestionRun(Base):
    __tablename__ = "ingestion_runs"
    __table_args__ = (CheckConstraint(f"status IN ({_STATUSES})", name="status"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    # Null when the file matched no source template.
    source: Mapped[str | None] = mapped_column(String(32))
    file_name: Mapped[str] = mapped_column(String(255))
    status: Mapped[RunStatus] = mapped_column(String(16))
    rows_total: Mapped[int]
    rows_accepted: Mapped[int]
    rows_rejected: Mapped[int]
    date_from: Mapped[dt.date | None]
    date_to: Mapped[dt.date | None]
    # Capped sample of {line, errors, values}; rows_rejected holds the full count.
    rejected_rows: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
