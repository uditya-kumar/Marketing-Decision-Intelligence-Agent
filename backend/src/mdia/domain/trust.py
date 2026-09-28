"""Data trust (FR-3.5, FR-5): can today's numbers be relied on?"""

from __future__ import annotations

import datetime as dt
import math
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from mdia.domain.kpi import change_pct
from mdia.domain.periods import Period, trailing
from mdia.domain.sources import SOURCES

if TYPE_CHECKING:
    from collections.abc import Collection, Iterable, Mapping

    import pandas as pd

    from mdia.domain.kpi import Metric
    from mdia.domain.sources import Source

TrustStatus = Literal["ok", "warning", "broken"]

# Gaps are only reported inside this recent window; old gaps don't affect today's numbers.
FRESHNESS_DAYS = 28
TRACKING_WINDOW_DAYS = 3
TRACKING_BASELINE_DAYS = 28
MIN_BASELINE_DAYS = 14
MIN_WINDOW_ORDERS = 30
# Recent conversions per store order, relative to the channel's baseline. On the 365-day
# evaluation data, ordinary days (festive peaks and real performance problems included)
# stay above ~0.68, while a broken pixel falls to ~0.15 within three days.
TRACKING_WARNING = 0.6
TRACKING_BROKEN = 0.45
# ROAS and CPA are built on platform-reported conversions; revenue, spend and MER are not.
PLATFORM_METRICS: tuple[Metric, ...] = ("roas", "cpa")

_SEVERITY: dict[TrustStatus, int] = {"ok": 0, "warning": 1, "broken": 2}


@dataclass(frozen=True, slots=True)
class Freshness:
    last_date: dt.date | None
    # Days the source trails the newest data from any source.
    days_behind: int
    # Days with no rows inside the recent window, between the source's first and last day.
    missing_dates: list[dt.date]

    @property
    def status(self) -> TrustStatus:
        if self.last_date is None:
            return "broken"
        return "warning" if self.days_behind or self.missing_dates else "ok"


@dataclass(frozen=True, slots=True)
class TrackingCheck:
    status: TrustStatus
    # Recent conversions per store order divided by the baseline's; 1.0 is normal.
    ratio_change: float
    # First day of the current run of low days, when the status isn't ok.
    since: dt.date | None
    conversions_change_pct: float | None
    orders_change_pct: float | None


@dataclass(frozen=True, slots=True)
class SourceTrust:
    source: Source
    status: TrustStatus
    freshness: Freshness
    tracking: TrackingCheck | None


def as_of_date(
    latest_by_source: Mapping[Source, dt.date | None],
    required: Iterable[Source] = SOURCES,
) -> dt.date | None:
    """Return the earliest of the required sources' latest dates.

    Anything later is missing at least one source, so blended metrics such as MER
    would be wrong for it. ``None`` until every required source has some data.
    """
    latest = [latest_by_source.get(source) for source in required]
    if any(day is None for day in latest):
        return None
    return min(day for day in latest if day is not None)


def missing_sources(
    latest_by_source: Mapping[Source, dt.date | None],
    required: Iterable[Source] = SOURCES,
) -> list[Source]:
    return [source for source in required if latest_by_source.get(source) is None]


def check_freshness(
    dates: Collection[dt.date],
    first: dt.date | None,
    last: dt.date | None,
    newest: dt.date,
    window_days: int = FRESHNESS_DAYS,
) -> Freshness:
    """How far a source trails ``newest``, and the days missing inside the recent window.

    ``dates`` are the days the source has rows for (at least those in the window);
    ``first`` / ``last`` bound all its data, ``None`` when it has none.
    """
    if first is None or last is None:
        return Freshness(None, 0, [])
    start = max(first, trailing(newest, window_days).start)
    gaps = [day for day in Period(start, last).dates() if day not in dates] if start <= last else []
    return Freshness(last, (newest - last).days, gaps)


def check_tracking(
    conversions: pd.Series,
    orders: pd.Series,
    as_of: dt.date,
) -> TrackingCheck | None:
    """Compare a channel's reported conversions per store order with its own baseline.

    Both series are indexed by date. A pixel that stops firing drops the platform's
    conversions while real orders carry on, so the ratio collapses. Returns ``None`` when
    there's too little history or too few orders to judge.
    """
    window = trailing(as_of, TRACKING_WINDOW_DAYS)
    baseline = trailing(window.start - dt.timedelta(days=1), TRACKING_BASELINE_DAYS)
    conv_now, orders_now = _slice(conversions, window), _slice(orders, window)
    conv_base, orders_base = _slice(conversions, baseline), _slice(orders, baseline)
    daily_base = (conv_base / orders_base).dropna()
    if len(daily_base) < MIN_BASELINE_DAYS or orders_now.sum() < MIN_WINDOW_ORDERS:
        return None
    # The median ignores a few odd days (a past outage, a festive spike) in the baseline.
    typical = float(daily_base.median())
    if typical <= 0:
        return None
    ratio_change = float(conv_now.sum() / orders_now.sum()) / typical
    status: TrustStatus = (
        "broken"
        if ratio_change <= TRACKING_BROKEN
        else "warning"
        if ratio_change <= TRACKING_WARNING
        else "ok"
    )
    since = None if status == "ok" else _low_since(conversions / orders, typical, window)
    return TrackingCheck(
        status,
        ratio_change,
        since,
        change_pct(_daily_mean(conv_base), _daily_mean(conv_now)),
        change_pct(_daily_mean(orders_base), _daily_mean(orders_now)),
    )


def assess_source(
    source: Source, freshness: Freshness, tracking: TrackingCheck | None = None
) -> SourceTrust:
    statuses = [freshness.status, tracking.status if tracking else "ok"]
    return SourceTrust(source, worst(statuses), freshness, tracking)


def worst(statuses: Iterable[TrustStatus]) -> TrustStatus:
    return max(statuses, key=_SEVERITY.__getitem__, default="ok")


def unreliable_metrics(sources: Iterable[SourceTrust]) -> set[Metric]:
    """KPIs that can't be trusted: platform-based ones while any ad tracking is broken."""
    broken = any(s.tracking is not None and s.tracking.status == "broken" for s in sources)
    return set(PLATFORM_METRICS) if broken else set()


def _slice(series: pd.Series, period: Period) -> pd.Series:
    return series.reindex(period.dates())


def _daily_mean(series: pd.Series) -> float | None:
    value = float(series.mean())
    return None if math.isnan(value) else value


def _low_since(daily_ratio: pd.Series, typical: float, window: Period) -> dt.date:
    """The first day of the latest run of low days, walking back from the window's end.

    Falls back to the window's start when the newest days have already recovered.
    """
    since = None
    for day in trailing(window.end, TRACKING_BASELINE_DAYS).dates()[::-1]:
        low = _is_low(daily_ratio.get(day), typical)
        if low:
            since = day
        elif since is not None or day < window.start:
            break
    return since or window.start


def _is_low(value: float | None, typical: float) -> bool:
    return value is not None and not math.isnan(value) and value / typical <= TRACKING_WARNING
