"""Analysis runs and the opportunities they find (FR-6.4, FR-8, FR-9).

Signals, evidence, diagnosis and recommendation are JSONB: they are read and written
whole, always belong to exactly one opportunity, and their shape is owned by
``domain/`` and ``agents/schemas.py`` rather than by the database.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal
from typing import Any, Literal, get_args

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from mdia.db.base import Base

AnalysisStatus = Literal["running", "done", "failed"]
OpportunityStatus = Literal["open", "dismissed", "experimenting", "resolved"]
DiagnosisSource = Literal["llm", "rules"]

SCORE = Numeric(16, 2)


def _one_of(column: str, values: tuple[str, ...]) -> CheckConstraint:
    allowed = ", ".join(f"'{value}'" for value in values)
    return CheckConstraint(f"{column} IN ({allowed})", name=column)


class AnalysisRun(Base):
    """One sweep of the detectors over the data, kicked off after an upload."""

    __tablename__ = "analysis_runs"
    __table_args__ = (_one_of("status", get_args(AnalysisStatus)),)

    id: Mapped[int] = mapped_column(primary_key=True)
    status: Mapped[AnalysisStatus] = mapped_column(String(16))
    # The last day every source covers; the window the run analysed ends here.
    as_of_date: Mapped[dt.date]
    signal_count: Mapped[int] = mapped_column(default=0)
    opportunity_count: Mapped[int] = mapped_column(default=0)
    # How many opportunities the LLM diagnosed, as opposed to the rule fallback (FR-8).
    llm_count: Mapped[int] = mapped_column(default=0)
    error: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    finished_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))


class Opportunity(Base):
    """One entity worth a marketer's attention, refreshed in place by every run."""

    __tablename__ = "opportunities"
    __table_args__ = (
        _one_of("kind", ("issue", "win")),
        _one_of("status", get_args(OpportunityStatus)),
        _one_of("diagnosis_source", get_args(DiagnosisSource)),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    # Stable across runs (``level:key``), so a continuing problem keeps one row.
    key: Mapped[str] = mapped_column(String(128), unique=True)
    analysis_run_id: Mapped[int] = mapped_column(ForeignKey("analysis_runs.id"))
    kind: Mapped[str] = mapped_column(String(8))
    status: Mapped[OpportunityStatus] = mapped_column(String(16), default="open")
    entity_level: Mapped[str] = mapped_column(String(16))
    entity_key: Mapped[str] = mapped_column(String(96))
    entity_name: Mapped[str] = mapped_column(String(255))
    channel_id: Mapped[str | None] = mapped_column(String(32))
    window_start: Mapped[dt.date]
    window_end: Mapped[dt.date]
    # Detection history, for days-to-detect and for "this has been going on a while".
    first_seen_date: Mapped[dt.date]
    last_seen_date: Mapped[dt.date]
    primary_metric: Mapped[str] = mapped_column(String(32))
    primary_detector: Mapped[str] = mapped_column(String(32))
    impact: Mapped[Decimal] = mapped_column(SCORE)
    score: Mapped[Decimal] = mapped_column(SCORE)
    signals: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    evidence: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    diagnosis: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    recommendation: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    priority: Mapped[Decimal | None] = mapped_column(SCORE)
    diagnosis_source: Mapped[DiagnosisSource | None] = mapped_column(String(8))
    dismissed_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
