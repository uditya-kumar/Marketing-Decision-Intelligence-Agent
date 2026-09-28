"""API DTOs for the analysis run (``/analysis/status``)."""

from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, ConfigDict

from mdia.models.analysis import AnalysisStatus


class AnalysisStatusOut(BaseModel):
    """The latest run, or an empty one before anything has been analysed."""

    model_config = ConfigDict(from_attributes=True)

    status: AnalysisStatus | None
    as_of_date: dt.date | None
    signal_count: int
    opportunity_count: int
    started_at: dt.datetime | None
    finished_at: dt.datetime | None
    error: str | None
