"""Detectors (FR-6.1): aggregated measures in, signals out.

A detector answers "did this entity move enough to be worth a look?" and nothing
else — no money, no ranking, no suppression (those live in ``scoring.py``). Every
detector is a pure function over :class:`Window` objects, so the same code serves
a channel, a creative or an age group.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

from mdia.domain.goals import goal_status
from mdia.domain.kpi import change_pct, definition, higher_is_better, ratio

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from mdia.domain.kpi import Kpi, Metric
    from mdia.domain.periods import Period
    from mdia.domain.sources import Channel
    from mdia.domain.trust import TrackingCheck

# The window a detector looks at, and the stretch of history it is compared with.
WINDOW_DAYS = 7
BASELINE_DAYS = 28
# Smaller moves are noise at this sample size; a segment has to differ harder still.
MIN_CHANGE_PCT = 15.0
MIN_DIVERGENCE_PCT = 25.0
# A funnel rate pools every session a channel bought, so a page broken for part of that
# traffic only ever shows as a small shift. It gets a lower bar, and ``stands_out`` below
# is what keeps that from turning into noise.
MIN_FUNNEL_PCT = 10.0
# Weeks of history a movement is held against, and how few of them still allow a verdict.
WEEKS_COMPARED = BASELINE_DAYS // WINDOW_DAYS
MIN_WEEKS = 3
# How far past the most extreme of those weeks the recent one has to sit.
MIN_MARGIN_PCT = 5.0
# Sales arrive one at a time, so a ratio built on n of them carries roughly 1/sqrt(n) of
# noise by itself. A movement has to clear this many of those before the data can tell it
# apart from luck; two is the usual "outside normal" line.
NOISE_SIGMAS = 2.0

EntityLevel = Literal[
    "account", "channel", "campaign", "ad_set", "creative", "age_group", "source"
]  # fmt: skip

Detector = Literal[
    "baseline_change", "goal_breach", "funnel_drop", "segment_divergence", "tracking_break"
]  # fmt: skip

FUNNEL_METRICS: tuple[Kpi, ...] = ("bounce_rate", "atc_rate", "checkout_rate", "purchase_rate")

# How much of a measure has to be there before a movement in it means anything.
MIN_SAMPLE: dict[str, float] = {
    "impressions": 5_000,
    "reach": 5_000,
    "clicks": 100,
    "spend": 5_000,
    "platform_conversions": 30,
    "sessions": 300,
    "add_to_cart": 30,
    "checkout": 20,
    "store_orders": 30,
}
# Rupees are only as trustworthy as the sales behind them: ROAS off three purchases is
# noise however much was spent, so a revenue measure is judged on its own conversions.
_BACKED_BY: dict[str, str] = {
    "platform_revenue": "platform_conversions",
    "store_revenue": "store_orders",
}
# Rupees spent arrive smoothly over a week; everything else here is counted events, and
# it is those that make a ratio jumpy when there are few of them.
_COUNTS: frozenset[str] = frozenset(MIN_SAMPLE) - {"spend"}


@dataclass(frozen=True, slots=True)
class Entity:
    """What a signal is about: an account, a channel, or something inside one."""

    level: EntityLevel
    key: str
    name: str
    # The channel that pays for this entity, so trust gating can reach it.
    channel: Channel | None = None
    # Entity IDs from the top down, used for breadcrumbs and for dropping a
    # parent's signal when a child explains the same movement.
    ancestors: tuple[str, ...] = ()

    @property
    def id(self) -> str:
        return f"{self.level}:{self.key}"


@dataclass(frozen=True, slots=True)
class Window:
    """Base measures summed over a period, plus the ratios they allow."""

    period: Period
    measures: Mapping[str, float]

    def value(self, metric: Metric) -> float | None:
        """The metric over the whole window: a ratio of sums, or a measure per day."""
        kpi = definition(metric)
        if kpi is None:
            total = self.measures.get(metric)
            return None if total is None else total / self.period.days
        return ratio(
            self.measures.get(kpi.numerator), self.measures.get(kpi.denominator), kpi.scale
        )

    def sample(self, measure: str) -> float:
        """How much of ``measure`` this window holds, counting a missing one as none."""
        return self.measures.get(measure) or 0.0


@dataclass(frozen=True, slots=True)
class Signal:
    """One movement worth explaining (FR-6.3)."""

    id: str
    detector: Detector
    metric: Metric
    entity: Entity
    window: Period
    current: float | None
    baseline: float | None
    change_pct: float | None
    # Whether the move went the wrong way; wins are signals too.
    adverse: bool
    # The window's base measures, kept so scoring and evidence need no second query.
    measures: Mapping[str, float] = field(default_factory=dict)
    # The baseline's, so the evidence tree (FR-8.1) can decompose the move without one either.
    baseline_measures: Mapping[str, float] = field(default_factory=dict)
    # Filled in by ``scoring.rank``; detectors know nothing about money.
    impact: float = 0.0
    score: float = 0.0


_TAGS: dict[Detector, str] = {
    "baseline_change": "chg",
    "goal_breach": "goal",
    "funnel_drop": "fun",
    "segment_divergence": "seg",
    "tracking_break": "trk",
}


def signal_id(detector: Detector, entity: Entity, metric: Metric, window: Period) -> str:
    """Stable per entity, metric and window end, so a re-run reproduces it exactly."""
    return f"{_TAGS[detector]}|{entity.id}|{metric}|{window.end:%Y%m%d}"


def enough_sample(metric: Metric, window: Window) -> bool:
    """Whether there is enough behind ``metric`` for a movement in it to mean anything.

    Both sides of a ratio have to clear their own floor: ROAS needs the spend *and*
    the sales that earned the revenue.
    """
    kpi = definition(metric)
    measures = (kpi.numerator, kpi.denominator) if kpi else (metric,)
    return all(_clears(measure, window) for measure in measures)


def _clears(measure: str, window: Window) -> bool:
    backing = _BACKED_BY.get(measure, measure)
    return window.sample(backing) >= MIN_SAMPLE.get(backing, 0.0)


def noise_floor(metric: Metric, window: Window, *, floor: float = MIN_CHANGE_PCT) -> float:
    """How big a move in ``metric`` has to be before this much data can tell it apart.

    Forty sales carry about sixteen per cent of noise on their own, so the bar that is
    strict for a channel's ROAS says nothing about one creative's. The scarcest count
    behind the metric sets the bar, and it never drops below ``floor``.
    """
    counts = [window.sample(measure) for measure in _counts_behind(metric)]
    scarcest = min((count for count in counts if count > 0), default=0.0)
    return floor if scarcest <= 0 else max(floor, NOISE_SIGMAS * 100 / math.sqrt(scarcest))


def _counts_behind(metric: Metric) -> list[str]:
    """The counted events a metric is built on, revenue read as the sales that earned it."""
    kpi = definition(metric)
    sides = (kpi.numerator, kpi.denominator) if kpi else (metric,)
    return [backing for side in sides if (backing := _BACKED_BY.get(side, side)) in _COUNTS]


def stands_out(value: float, weeks: Sequence[float], *, margin_pct: float = MIN_MARGIN_PCT) -> bool:
    """Whether ``value`` sits outside every week of history it is given.

    Fifteen per cent off a four-week average is easy to reach for anything small, and a
    week that stays inside the last four is how the entity always behaves. Being more
    extreme than any of them is what makes the movement news. Too little history to
    judge on means the movement gets the benefit of the doubt.
    """
    if len(weeks) < MIN_WEEKS:
        return True
    margin = 1 + margin_pct / 100
    return value > max(weeks) * margin or value < min(weeks) / margin


def _compare(
    entity: Entity,
    metric: Metric,
    current: Window,
    baseline: Window,
    *,
    detector: Detector,
    min_change: float,
    weeks: Sequence[Window] = (),
) -> Signal | None:
    if not enough_sample(metric, current):
        return None
    now = current.value(metric)
    before = baseline.value(metric)
    change = change_pct(before, now)
    if (
        now is None
        or change is None
        or abs(change) < noise_floor(metric, current, floor=min_change)
    ):
        return None
    if not stands_out(now, [value for week in weeks if (value := week.value(metric)) is not None]):
        return None
    direction = higher_is_better(metric)
    return Signal(
        id=signal_id(detector, entity, metric, current.period),
        detector=detector,
        metric=metric,
        entity=entity,
        window=current.period,
        current=now,
        baseline=before,
        change_pct=change,
        adverse=direction is not None and (change < 0) == direction,
        measures=current.measures,
        baseline_measures=baseline.measures,
    )


def baseline_change(
    entity: Entity,
    metric: Metric,
    current: Window,
    baseline: Window,
    *,
    min_change: float = MIN_CHANGE_PCT,
    weeks: Sequence[Window] = (),
) -> Signal | None:
    """The recent window against its rolling baseline, and against each week of it."""
    return _compare(
        entity,
        metric,
        current,
        baseline,
        detector="baseline_change",
        min_change=min_change,
        weeks=weeks,
    )


def goal_breach(
    entity: Entity,
    metric: Metric,
    current: Window,
    target: float,
    *,
    prefer_higher: bool | None = None,
) -> Signal | None:
    """A signal only while the metric is ``behind`` its target; the target is the baseline."""
    if not enough_sample(metric, current):
        return None
    value = current.value(metric)
    direction = higher_is_better(metric) if prefer_higher is None else prefer_higher
    if value is None or direction is None:
        return None
    if goal_status(value, target, higher_is_better=direction) != "behind":
        return None
    return Signal(
        id=signal_id("goal_breach", entity, metric, current.period),
        detector="goal_breach",
        metric=metric,
        entity=entity,
        window=current.period,
        current=value,
        baseline=target,
        change_pct=change_pct(target, value),
        adverse=True,
        measures=current.measures,
    )


def funnel_drop(
    entity: Entity, current: Window, baseline: Window, *, weeks: Sequence[Window] = ()
) -> list[Signal]:
    """Web funnel steps that got worse; a step that improved is not a problem."""
    found = (
        _compare(
            entity,
            metric,
            current,
            baseline,
            detector="funnel_drop",
            min_change=MIN_FUNNEL_PCT,
            weeks=weeks,
        )
        for metric in FUNNEL_METRICS
    )
    return [signal for signal in found if signal is not None and signal.adverse]


def segment_divergence(
    entity: Entity,
    metric: Metric,
    segment: Window,
    peers: Window,
    *,
    min_change: float = MIN_DIVERGENCE_PCT,
) -> Signal | None:
    """One segment dragging its ad set, against the pooled rest of it.

    Only the losing side is a finding: in every ad set some age group is above the rest
    and some is below, so "better than its peers" would fire on all of them forever.
    """
    found = _compare(
        entity, metric, segment, peers, detector="segment_divergence", min_change=min_change
    )
    return found if found is not None and found.adverse else None


def tracking_break(entity: Entity, check: TrackingCheck, current: Window) -> Signal | None:
    """Turn the FR-5.4 tracking verdict into a signal so it can become an opportunity."""
    if check.status == "ok":
        return None
    return Signal(
        id=signal_id("tracking_break", entity, "platform_conversions", current.period),
        detector="tracking_break",
        metric="platform_conversions",
        entity=entity,
        window=current.period,
        # The conversions-per-order ratio as a share of its own history: 1.0 is normal.
        current=check.ratio_change,
        baseline=1.0,
        change_pct=(check.ratio_change - 1) * 100,
        adverse=True,
        measures=current.measures,
    )
