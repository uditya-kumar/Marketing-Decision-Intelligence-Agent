"""API DTO for the Today screen (``/today``)."""

from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, ConfigDict

from mdia.schemas.experiments import ExperimentOut
from mdia.schemas.metrics import KpiSummaryOut, PeriodOut, TrendPointOut
from mdia.schemas.opportunities import OpportunityOut
from mdia.schemas.trust import PacingViewOut, TrustOut


class ExperimentsTodayOut(BaseModel):
    """The Experiments strip: "Creative rotation · Day 4/7 · 1 awaiting approval"."""

    model_config = ConfigDict(from_attributes=True)

    running: list[ExperimentOut]
    completed: list[ExperimentOut]
    awaiting: int


class TodayOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    as_of_date: dt.date | None
    configured: bool
    period: PeriodOut | None
    kpis: list[KpiSummaryOut]
    trend: list[TrendPointOut]
    trust: TrustOut
    pacing: PacingViewOut
    attention: list[OpportunityOut]
    wins: list[OpportunityOut]
    experiments: ExperimentsTodayOut
    analysing: bool
