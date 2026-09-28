"""The weekly report (FR-11): one row per week, generated on request.

The payload and the narrative are JSONB for the same reason as the analysis columns:
they are written and read whole, belong to exactly one week, and their shape is owned
by ``domain/reports.py`` and ``agents/schemas.py``. Storing the payload beside the
prose is what lets a report be re-read months later without recomputing the week.
"""

from __future__ import annotations

import datetime as dt
from typing import Any, Literal, get_args

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from mdia.db.base import Base
from mdia.models.analysis import one_of

ReportSource = Literal["llm", "template"]


class WeeklyReport(Base):
    """One week as generated: the facts, the words, and whether the words were checked."""

    __tablename__ = "reports"
    __table_args__ = (one_of("source", get_args(ReportSource)),)

    id: Mapped[int] = mapped_column(primary_key=True)
    week_start: Mapped[dt.date]
    # Generating the same week again replaces the row, so the history has no duplicates.
    week_end: Mapped[dt.date] = mapped_column(unique=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    # ``{"summary": [...], "detail": [...]}``: the founder lines and the team sections.
    narrative: Mapped[dict[str, Any]] = mapped_column(JSONB)
    source: Mapped[ReportSource] = mapped_column(String(8))
    # Whether the narrative passed the grounding guard; a template report never claims to.
    grounded: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
