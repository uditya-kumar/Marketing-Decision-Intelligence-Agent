"""KPI queries (FR-4.3): summed from the fact tables on request; nothing is pre-aggregated."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

import pandas as pd

from mdia.domain.goals import break_even_roas, goal_status, prorated_target
from mdia.domain.kpi import add_kpis, change_pct, higher_is_better, metric_values
from mdia.domain.periods import Period, days_in_month, trailing
from mdia.domain.trust import as_of_date
from mdia.repositories.facts import AD_MEASURES, FactRepository
from mdia.repositories.metrics import MetricsRepository

if TYPE_CHECKING:
    import datetime as dt
    from collections.abc import Collection

    from sqlalchemy.orm import Session

    from mdia.domain.goals import GoalStatus
    from mdia.domain.kpi import Dimension, Metric
    from mdia.models import BusinessSettings

TODAY_METRICS: tuple[Metric, ...] = ("store_revenue", "spend", "roas", "mer", "cpa")
COMPARE_DAYS = 7  # "vs last week"
TREND_DAYS = 30
STORE_MEASURES = ("store_orders", "store_revenue")


@dataclass(frozen=True, slots=True)
class Goal:
    target: float
    status: GoalStatus


@dataclass(frozen=True, slots=True)
class KpiSummary:
    metric: Metric
    value: float | None
    previous: float | None
    change_pct: float | None
    higher_is_better: bool | None
    goal: Goal | None
    # False when the metric rests on data that failed a trust check (FR-5).
    reliable: bool


@dataclass(frozen=True, slots=True)
class TrendPoint:
    date: dt.date
    store_revenue: float | None
    spend: float | None
    roas: float | None
    mer: float | None
    cpa: float | None


@dataclass(frozen=True, slots=True)
class TodayKpis:
    period: Period
    kpis: list[KpiSummary]
    trend: list[TrendPoint]


@dataclass(frozen=True, slots=True)
class SeriesPoint:
    date: dt.date
    value: float | None


@dataclass(frozen=True, slots=True)
class MetricSeries:
    key: str
    name: str
    value: float | None
    previous: float | None
    change_pct: float | None
    points: list[SeriesPoint]


@dataclass(frozen=True, slots=True)
class MetricsView:
    metric: Metric
    dimension: Dimension | None
    period: Period | None
    series: list[MetricSeries]


class MetricsService:
    def __init__(self, session: Session) -> None:
        self._metrics = MetricsRepository(session)
        self._facts = FactRepository(session)

    def as_of(self) -> dt.date | None:
        return as_of_date({c.source: c.last_date for c in self._facts.coverage()})

    def today(
        self,
        as_of: dt.date,
        settings: BusinessSettings | None,
        unreliable: Collection[Metric] = (),
    ) -> TodayKpis:
        """Headline KPIs for the week to ``as_of`` against the week before, plus a 30-day trend."""
        current = trailing(as_of, COMPARE_DAYS)
        trend = trailing(as_of, TREND_DAYS)
        frame = self._daily(Period(min(trend.start, current.previous().start), as_of))
        now, before = _totals(frame, current), _totals(frame, current.previous())
        targets = _targets(settings, as_of)
        summaries = [
            KpiSummary(
                metric,
                now[metric],
                before[metric],
                change_pct(before[metric], now[metric]),
                higher_is_better(metric),
                _goal(metric, now[metric], targets.get(metric)),
                metric not in unreliable,
            )
            for metric in TODAY_METRICS
        ]
        daily = add_kpis(frame.loc[trend.dates()])
        points = [
            TrendPoint(day, **{m: _value(row[m]) for m in TODAY_METRICS})
            for day, row in zip(trend.dates(), daily.to_dict("records"), strict=True)
        ]
        return TodayKpis(current, summaries, points)

    def series(
        self, metric: Metric, dimension: Dimension | None, days: int, end: dt.date | None
    ) -> MetricsView:
        """``metric`` per day over ``days`` days, per ``dimension`` value, vs the prior period."""
        end = end or self.as_of()
        if end is None:
            return MetricsView(metric, dimension, None, [])
        period = trailing(end, days)
        span = Period(period.previous().start, period.end)
        if dimension is None:
            groups = [("total", "All channels", self._daily(span))]
        else:
            rows = pd.DataFrame(
                self._metrics.ad_daily(span, dimension),
                columns=["date", "key", "name", *AD_MEASURES],
            )
            groups = [
                (str(key), str(name), _complete(group.drop(columns=["key", "name"]), span))
                for (key, name), group in rows.groupby(["key", "name"])
            ]
        series = [_series(key, name, frame, metric, period) for key, name, frame in groups]
        return MetricsView(metric, dimension, period, sorted(series, key=lambda s: s.name))

    def _daily(self, span: Period) -> pd.DataFrame:
        """Ad and store measures per day, one row for every day in ``span``."""
        ads = pd.DataFrame(self._metrics.ad_daily(span), columns=["date", *AD_MEASURES])
        store = pd.DataFrame(self._metrics.store_daily(span), columns=["date", *STORE_MEASURES])
        return _complete(ads.merge(store, on="date", how="outer"), span)


def _complete(rows: pd.DataFrame, span: Period) -> pd.DataFrame:
    """Index by date and add the days with no rows, so gaps show as missing, not zero."""
    return rows.set_index("date").astype(float).reindex(span.dates())


def _totals(frame: pd.DataFrame, period: Period) -> dict[Metric, float | None]:
    sums = frame.loc[period.dates()].sum(min_count=1)
    return metric_values({str(measure): value for measure, value in sums.items()})


def _series(
    key: str, name: str, frame: pd.DataFrame, metric: Metric, period: Period
) -> MetricSeries:
    now, before = _totals(frame, period)[metric], _totals(frame, period.previous())[metric]
    daily = add_kpis(frame.loc[period.dates()])
    # Store metrics such as MER have no per-channel breakdown, so sliced series stay empty.
    values = daily[metric].tolist() if metric in daily else [math.nan] * period.days
    points = [
        SeriesPoint(day, _value(value)) for day, value in zip(period.dates(), values, strict=True)
    ]
    return MetricSeries(key, name, now, before, change_pct(before, now), points)


def _targets(settings: BusinessSettings | None, as_of: dt.date) -> dict[Metric, float]:
    """Goal markers for the Today strip. MER is judged against break-even, and revenue
    against the week's share of the monthly goal."""
    if settings is None:
        return {}
    targets: dict[Metric, float] = {"mer": break_even_roas(float(settings.gross_margin_pct))}
    if settings.target_roas is not None:
        targets["roas"] = float(settings.target_roas)
    if settings.target_cpa is not None:
        targets["cpa"] = float(settings.target_cpa)
    if settings.monthly_revenue_goal is not None:
        monthly = float(settings.monthly_revenue_goal)
        targets["store_revenue"] = prorated_target(monthly, COMPARE_DAYS, days_in_month(as_of))
    return targets


def _goal(metric: Metric, value: float | None, target: float | None) -> Goal | None:
    if value is None or target is None:
        return None
    better = higher_is_better(metric) is not False
    return Goal(target, goal_status(value, target, higher_is_better=better))


def _value(value: float) -> float | None:
    return None if math.isnan(value) else float(value)
