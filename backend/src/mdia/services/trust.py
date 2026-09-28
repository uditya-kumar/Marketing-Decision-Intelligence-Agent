"""Data trust per source (FR-5), computed on request and never stored."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import pandas as pd

from mdia.domain.periods import trailing
from mdia.domain.sources import CHANNELS, SOURCES
from mdia.domain.trust import (
    FRESHNESS_DAYS,
    TRACKING_BASELINE_DAYS,
    TRACKING_WINDOW_DAYS,
    Freshness,
    TrackingCheck,
    as_of_date,
    assess_source,
    check_freshness,
    check_tracking,
)
from mdia.repositories.facts import FactRepository
from mdia.repositories.metrics import MetricsRepository

if TYPE_CHECKING:
    import datetime as dt

    from sqlalchemy.orm import Session

    from mdia.domain.sources import Source
    from mdia.domain.trust import SourceTrust
    from mdia.repositories.facts import SourceCoverage


@dataclass(frozen=True, slots=True)
class TrustView:
    as_of_date: dt.date | None
    sources: list[SourceTrust]


class TrustService:
    def __init__(self, session: Session) -> None:
        self._facts = FactRepository(session)
        self._metrics = MetricsRepository(session)

    def check(self, coverage: list[SourceCoverage] | None = None) -> TrustView:
        """Freshness of every source and a tracking check per ad channel.

        ``coverage`` can be passed in by a caller that already fetched it.
        """
        found = {c.source: c for c in (self._facts.coverage() if coverage is None else coverage)}
        as_of = as_of_date({source: c.last_date for source, c in found.items()})
        newest = max((c.last_date for c in found.values() if c.last_date), default=None)
        if newest is None:
            empty = Freshness(None, 0, [])
            return TrustView(None, [assess_source(source, empty) for source in SOURCES])
        dates = self._facts.dates_by_source(trailing(newest, FRESHNESS_DAYS))
        tracking = self._tracking(as_of) if as_of else {}
        sources = []
        for source in SOURCES:
            c = found.get(source)
            first, last = (c.first_date, c.last_date) if c else (None, None)
            freshness = check_freshness(dates.get(source, set()), first, last, newest)
            sources.append(assess_source(source, freshness, tracking.get(source)))
        return TrustView(as_of, sources)

    def _tracking(self, as_of: dt.date) -> dict[Source, TrackingCheck]:
        span = trailing(as_of, TRACKING_WINDOW_DAYS + TRACKING_BASELINE_DAYS)
        ads = pd.DataFrame(
            self._metrics.ad_daily(span, "channel"),
            columns=["date", "key", "name", "platform_conversions"],
        )
        conversions = ads.pivot_table(
            index="date", columns="key", values="platform_conversions", aggfunc="sum"
        ).astype(float)
        store = pd.DataFrame(self._metrics.store_daily(span), columns=["date", "store_orders"])
        orders = store.set_index("date")["store_orders"].astype(float)
        checks: dict[Source, TrackingCheck] = {}
        for channel in CHANNELS:
            if channel not in conversions:
                continue
            check = check_tracking(conversions[channel], orders, as_of)
            if check is not None:
                checks[channel] = check
        return checks
