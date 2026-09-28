"""API DTOs for the weekly report (``/reports``).

The payload stays in the database: the screen shows the prose, and every number in it
was checked against those facts before the report was stored (FR-11.2).
"""

from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, ConfigDict

from mdia.models.reports import ReportSource
from mdia.schemas.metrics import PeriodOut


class _Out(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ReportOut(_Out):
    """One week's report: the founder summary, the team detail, and how it was written."""

    id: int
    week: PeriodOut
    summary: list[str]
    detail: list[str]
    source: ReportSource
    grounded: bool
    created_at: dt.datetime


class ReportListOut(_Out):
    reports: list[ReportOut]
    # The week a fresh report would cover, which is what the picker opens on.
    next_week_end: dt.date | None


class GenerateReportIn(BaseModel):
    """Which week to report on; the latest day of data when left out."""

    model_config = ConfigDict(extra="forbid")

    week_end: dt.date | None = None
