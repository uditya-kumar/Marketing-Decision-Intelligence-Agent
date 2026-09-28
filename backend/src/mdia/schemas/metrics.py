"""API DTOs for KPI series (``/metrics``) and the Today summary (``/today``)."""

from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, ConfigDict

from mdia.domain.goals import GoalStatus
from mdia.domain.kpi import Dimension, Metric


class _Out(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class PeriodOut(_Out):
    start: dt.date
    end: dt.date


class GoalOut(_Out):
    target: float
    status: GoalStatus


class KpiSummaryOut(_Out):
    metric: Metric
    value: float | None
    previous: float | None
    change_pct: float | None
    higher_is_better: bool | None
    goal: GoalOut | None


class TrendPointOut(_Out):
    date: dt.date
    store_revenue: float | None
    spend: float | None
    roas: float | None
    mer: float | None
    cpa: float | None


class TodayOut(_Out):
    as_of_date: dt.date | None
    configured: bool
    period: PeriodOut | None
    kpis: list[KpiSummaryOut]
    trend: list[TrendPointOut]


class SeriesPointOut(_Out):
    date: dt.date
    value: float | None


class MetricSeriesOut(_Out):
    key: str
    name: str
    value: float | None
    previous: float | None
    change_pct: float | None
    points: list[SeriesPointOut]


class MetricsOut(_Out):
    metric: Metric
    dimension: Dimension | None
    period: PeriodOut | None
    series: list[MetricSeriesOut]
