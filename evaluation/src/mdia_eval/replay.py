"""Replay the FR-6 sweep over a whole dataset, one as-of date at a time.

This is what an operator would have seen had they uploaded every day: the same
``analyse`` the backend runs, with the trust checks recomputed at each date so
suppression behaves exactly as it would in production.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

from mdia.domain.detection import Context, analyse
from mdia.domain.periods import Period
from mdia.domain.scoring import MIN_SCORE
from mdia.domain.signals import BASELINE_DAYS, WINDOW_DAYS
from mdia.domain.trust import check_tracking

from mdia_eval.facts import span

if TYPE_CHECKING:
    from collections.abc import Sequence

    import pandas as pd
    from mdia.domain.detection import Facts
    from mdia.domain.opportunities import Opportunity
    from mdia.domain.sources import Channel
    from mdia.domain.trust import TrackingCheck

    from mdia_eval.settings import EvalSettings

# A detector needs its baseline plus its window before it can say anything.
WARMUP_DAYS = BASELINE_DAYS + WINDOW_DAYS

type Series = tuple[pd.Series, pd.Series]


@dataclass(frozen=True, slots=True)
class Run:
    as_of: dt.date
    opportunities: list[Opportunity]
    tracking: dict[Channel, TrackingCheck]

    @property
    def broken(self) -> tuple[Channel, ...]:
        return tuple(c for c, check in self.tracking.items() if check.status == "broken")


def covered(runs: Sequence[Run]) -> Period:
    """The days the replay could see at all: the first detection window to the last day.

    A scenario that ended before this cannot be detected however good the detectors
    are, so the score counts it separately instead of against recall.
    """
    first = runs[0].as_of - dt.timedelta(days=WINDOW_DAYS - 1)
    return Period(first, runs[-1].as_of)


def replay(
    facts: Facts,
    settings: EvalSettings,
    *,
    min_score: float = MIN_SCORE,
    festive: bool = True,
) -> list[Run]:
    """One :class:`Run` per day the detectors have enough history for."""
    covered = span(facts)
    start = covered.start + dt.timedelta(days=WARMUP_DAYS)
    series = tracking_inputs(facts)
    runs = []
    for as_of in Period(start, covered.end).dates():
        checks = tracking_checks(series, as_of)
        context = Context(
            as_of=as_of,
            # Ground truth injects no account-goal scenarios, so account targets are left
            # out: they would only add findings this dataset cannot confirm or deny.
            targets={},
            month_budgets=settings.month_budgets(as_of),
            festive=settings.festive if festive else (),
            broken=tuple(c for c, check in checks.items() if check.status == "broken"),
            tracking=checks,
            min_score=min_score,
        )
        runs.append(Run(as_of, analyse(facts, context), checks))
    return runs


def tracking_checks(series: dict[Channel, Series], as_of: dt.date) -> dict[Channel, TrackingCheck]:
    """The trust verdict per channel on one date; channels without enough history drop out."""
    checks = {channel: check_tracking(*pair, as_of) for channel, pair in series.items()}
    return {channel: check for channel, check in checks.items() if check is not None}


def tracking_inputs(facts: Facts) -> dict[Channel, Series]:
    """Per channel: reported conversions by date, paired with the store's orders by date."""
    orders = facts.store.set_index("date")["store_orders"]
    by_channel = facts.ads.groupby(["channel_id", "date"])["platform_conversions"].sum()
    channels = by_channel.index.get_level_values("channel_id").unique()
    return {cast("Channel", str(c)): (by_channel.loc[c], orders) for c in channels}
