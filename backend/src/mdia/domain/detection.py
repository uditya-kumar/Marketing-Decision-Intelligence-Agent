"""Running every detector over a period's facts (FR-6).

Pure pandas in, opportunities out: the service hands over the frames it queried and
the settings it read, and gets back the ranked list. Which entities and metrics are
worth checking is decided here, in one place, so the sweep is easy to reason about.
"""

from __future__ import annotations

import datetime as dt
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, cast

import pandas as pd

from mdia.domain import signals as detectors
from mdia.domain.kpi import definition
from mdia.domain.opportunities import Opportunity, group
from mdia.domain.periods import Period, days_in_month, trailing
from mdia.domain.scoring import MIN_SCORE, rank
from mdia.domain.signals import (
    BASELINE_DAYS,
    WEEKS_COMPARED,
    WINDOW_DAYS,
    Entity,
    Window,
)
from mdia.domain.sources import PAID_WEB_SOURCES, SOURCE_LABELS

if TYPE_CHECKING:
    from collections.abc import Collection, Iterator, Mapping, Sequence

    from mdia.domain.kpi import Metric
    from mdia.domain.signals import EntityLevel, Signal
    from mdia.domain.sources import Channel
    from mdia.domain.trust import TrackingCheck

ACCOUNT = Entity("account", "all", "All channels")

# What is worth checking where: deeper levels carry the metrics you can act on there.
LEVEL_METRICS: dict[EntityLevel, tuple[Metric, ...]] = {
    "channel": ("cpa", "roas", "cpc", "cpm", "ctr", "cvr"),
    "campaign": ("cpa", "roas", "cvr", "cpc"),
    "ad_set": ("cpa", "roas", "cvr"),
    "creative": ("cpa", "roas", "ctr", "cpc", "frequency"),
}
# Blended metrics only exist for the account: the store doesn't know which ad paid.
ACCOUNT_METRICS: tuple[Metric, ...] = ("mer", "store_revenue", "roas", "cpa")
# An age group is compared with its ad set's other age groups, not with its own past.
SEGMENT_METRICS: tuple[Metric, ...] = ("cpa", "roas")

_KEY: dict[EntityLevel, str] = {
    "campaign": "campaign_id",
    "ad_set": "ad_set_id",
    "creative": "creative_id",
    "age_group": "segment",
}
_NAME: dict[EntityLevel, str] = {
    "campaign": "campaign_name",
    "ad_set": "ad_set_name",
    "creative": "creative_name",
    "age_group": "age_group",
}
# Parent levels of each level, top down; "channel" is the first key in every ad row.
_CHAIN: dict[EntityLevel, tuple[EntityLevel, ...]] = {
    "campaign": ("channel",),
    "ad_set": ("channel", "campaign"),
    "creative": ("channel", "campaign", "ad_set"),
    "age_group": ("channel", "campaign", "ad_set"),
}
_CHANNEL_KEY = "channel_id"
# Levels that are a thing inside their parent rather than a slice of it.
_COUNTED_LEVELS: tuple[EntityLevel, ...] = ("campaign", "ad_set", "creative")
_DIMENSIONS = frozenset(
    {"date", "source", "channel", "channel_name", _CHANNEL_KEY, *_KEY.values(), *_NAME.values()}
)


@dataclass(frozen=True, slots=True)
class Facts:
    """Daily rows for one span: ads sliced to the creative × age group, web and store."""

    ads: pd.DataFrame
    web: pd.DataFrame
    store: pd.DataFrame


@dataclass(frozen=True, slots=True)
class Context:
    """Everything outside the facts that the sweep needs (FR-1 settings, FR-5 trust)."""

    as_of: dt.date
    # Ratio metrics as the ratio itself; base measures as a total for the seven-day window.
    targets: Mapping[Metric, float]
    # Month-to-date budget per channel, against which overspend is a goal breach.
    month_budgets: Mapping[Channel, float]
    festive: Sequence[Period] = ()
    broken: Collection[Channel] = ()
    tracking: Mapping[Channel, TrackingCheck] = field(default_factory=dict)
    min_score: float = MIN_SCORE


def analyse(facts: Facts, context: Context) -> list[Opportunity]:
    """Detect, suppress, score and group: the whole of FR-6 in one call."""
    found = rank(
        detect(facts, context),
        festive=context.festive,
        broken=context.broken,
        min_score=context.min_score,
    )
    return group(found, children=_child_counts(facts.ads))


def detect(facts: Facts, context: Context) -> list[Signal]:
    """Every raw signal in the window ending on ``context.as_of``, unscored."""
    recent = trailing(context.as_of, WINDOW_DAYS)
    baseline = trailing(recent.start - dt.timedelta(days=1), BASELINE_DAYS)
    ads = _prepare(facts.ads)
    found = [
        *_account_signals(ads, facts.store, recent, baseline, context),
        *_level_signals(ads, recent, baseline),
        *_segment_signals(ads, recent),
        *_web_signals(facts.web, ads, recent, baseline),
        *_pacing_signals(ads, recent, context),
        *_tracking_signals(ads, recent, context),
    ]
    return found


def _prepare(ads: pd.DataFrame) -> pd.DataFrame:
    """Give every age group a key of its own; the label alone repeats across ad sets."""
    if ads.empty:
        return ads
    prepared = ads.copy()
    prepared["segment"] = prepared["ad_set_id"].astype(str) + "|" + prepared["age_group"]
    return prepared


def _measures(frame: pd.DataFrame) -> list[str]:
    return [column for column in frame.columns if column not in _DIMENSIONS]


def _totals(frame: pd.DataFrame, period: Period) -> dict[str, float]:
    if frame.empty:
        return {}
    rows = frame[frame["date"].isin(set(period.dates()))]
    sums = rows[_measures(frame)].sum(min_count=1)
    return {str(name): float(value) for name, value in sums.items() if not pd.isna(value)}


def _grouped(frame: pd.DataFrame, key: str, period: Period) -> dict[str, dict[str, float]]:
    """Base measures summed per ``key`` value over ``period``."""
    if frame.empty:
        return {}
    rows = frame[frame["date"].isin(set(period.dates()))]
    sums = rows.groupby(key, sort=False)[_measures(frame)].sum(min_count=1)
    return {
        str(name): {str(m): float(v) for m, v in row.items() if not pd.isna(v)}
        for name, row in sums.iterrows()
    }


def _weeks(baseline: Period) -> list[Period]:
    """The baseline cut into detection-length weeks, so a week can be judged against them."""
    starts = (
        baseline.start + dt.timedelta(days=WINDOW_DAYS * index) for index in range(WEEKS_COMPARED)
    )
    return [
        Period(start, min(start + dt.timedelta(days=WINDOW_DAYS - 1), baseline.end))
        for start in starts
        if start <= baseline.end
    ]


def _grouped_weeks(
    frame: pd.DataFrame, key: str, weeks: Sequence[Period]
) -> dict[str, list[Window]]:
    """Per ``key`` value, one window per week of the baseline it has data for."""
    per_week = [(week, _grouped(frame, key, week)) for week in weeks]
    found: dict[str, list[Window]] = defaultdict(list)
    for week, grouped in per_week:
        for entity_key, measures in grouped.items():
            found[entity_key].append(Window(week, measures))
    return found


def _entities(ads: pd.DataFrame, level: EntityLevel) -> dict[str, Entity]:
    key, name = _KEY[level], _NAME[level]
    columns = list(dict.fromkeys([key, name, _CHANNEL_KEY, *(_KEY[p] for p in _CHAIN[level][1:])]))
    rows = ads[columns].drop_duplicates(subset=key).to_dict("records")
    return {
        str(row[key]): Entity(
            level,
            str(row[key]),
            str(row[name]),
            channel=cast("Channel", row[_CHANNEL_KEY]),
            ancestors=(
                ACCOUNT.id,
                f"channel:{row[_CHANNEL_KEY]}",
                *(f"{p}:{row[_KEY[p]]}" for p in _CHAIN[level][1:]),
            ),
        )
        for row in rows
    }


def _child_counts(ads: pd.DataFrame) -> dict[str, int]:
    """How many children each entity has, so a broad move can be told from a narrow one.

    Age groups are left out: they are a slice of an ad set, not another thing inside it.
    """
    if ads.empty:
        return {}
    counts: Counter[str] = Counter({ACCOUNT.id: int(ads[_CHANNEL_KEY].nunique())})
    for level in _COUNTED_LEVELS:
        for entity in _entities(ads, level).values():
            counts[entity.ancestors[-1]] += 1
    return dict(counts)


def _channel_entity(channel: Channel) -> Entity:
    return Entity("channel", channel, SOURCE_LABELS[channel], channel, (ACCOUNT.id,))


def _level_signals(ads: pd.DataFrame, recent: Period, baseline: Period) -> Iterator[Signal]:
    """Rolling-baseline change for every entity at every level that has a name."""
    if ads.empty:
        return
    weeks = _weeks(baseline)
    for level, metrics in LEVEL_METRICS.items():
        key = _CHANNEL_KEY if level == "channel" else _KEY[level]
        entities = (
            {c: _channel_entity(cast("Channel", c)) for c in ads[_CHANNEL_KEY].unique()}
            if level == "channel"
            else _entities(ads, level)
        )
        now, before = _grouped(ads, key, recent), _grouped(ads, key, baseline)
        weekly = _grouped_weeks(ads, key, weeks)
        for entity_key, entity in entities.items():
            if entity_key not in now or entity_key not in before:
                continue
            current = Window(recent, now[entity_key])
            history = Window(baseline, before[entity_key])
            for metric in metrics:
                signal = detectors.baseline_change(
                    entity, metric, current, history, weeks=weekly[entity_key]
                )
                if signal is not None:
                    yield signal


def _segment_signals(ads: pd.DataFrame, recent: Period) -> Iterator[Signal]:
    """Each age group against the pooled other age groups of its own ad set."""
    if ads.empty:
        return
    entities = _entities(ads, "age_group")
    by_segment = _grouped(ads, "segment", recent)
    by_ad_set = _grouped(ads, "ad_set_id", recent)
    for key, entity in entities.items():
        segment = by_segment.get(key)
        ad_set = by_ad_set.get(key.split("|")[0])
        if segment is None or ad_set is None:
            continue
        peers = {measure: ad_set.get(measure, 0.0) - value for measure, value in segment.items()}
        for metric in SEGMENT_METRICS:
            signal = detectors.segment_divergence(
                entity, metric, Window(recent, segment), Window(recent, peers)
            )
            if signal is not None:
                yield signal


def _web_signals(
    web: pd.DataFrame, ads: pd.DataFrame, recent: Period, baseline: Period
) -> Iterator[Signal]:
    """Funnel-step drops for the site as a whole and for each channel's paid sessions.

    A funnel rate is not money, so the ad spend behind those sessions comes along to
    stand for what the drop is costing.
    """
    if web.empty:
        return
    weeks = _weeks(baseline)
    spend = _grouped(ads, _CHANNEL_KEY, recent)
    at_stake = {"spend": sum(measures.get("spend", 0.0) for measures in spend.values())}
    yield from detectors.funnel_drop(
        ACCOUNT,
        Window(recent, _totals(web, recent) | at_stake),
        Window(baseline, _totals(web, baseline)),
        weeks=[Window(week, _totals(web, week)) for week in weeks],
    )
    paid = web.assign(channel=web["source"].map(PAID_WEB_SOURCES)).dropna(subset=["channel"])
    now, before = _grouped(paid, "channel", recent), _grouped(paid, "channel", baseline)
    weekly = _grouped_weeks(paid, "channel", weeks)
    for key in now.keys() & before.keys():
        channel = cast("Channel", key)
        yield from detectors.funnel_drop(
            _channel_entity(channel),
            Window(recent, now[key] | {"spend": spend.get(key, {}).get("spend", 0.0)}),
            Window(baseline, before[key]),
            weeks=weekly[key],
        )


def _account_signals(
    ads: pd.DataFrame,
    store: pd.DataFrame,
    recent: Period,
    baseline: Period,
    context: Context,
) -> Iterator[Signal]:
    current = Window(recent, _totals(ads, recent) | _totals(store, recent))
    history = Window(baseline, _totals(ads, baseline) | _totals(store, baseline))
    weeks = [Window(week, _totals(ads, week) | _totals(store, week)) for week in _weeks(baseline)]
    for metric in ACCOUNT_METRICS:
        change = detectors.baseline_change(ACCOUNT, metric, current, history, weeks=weeks)
        if change is not None:
            yield change
        target = context.targets.get(metric)
        if target is not None:
            # A revenue goal covers the whole window; Window.value reports a daily rate.
            if definition(metric) is None:
                target /= recent.days
            breach = detectors.goal_breach(ACCOUNT, metric, current, target)
            if breach is not None:
                yield breach


def _pacing_signals(ads: pd.DataFrame, recent: Period, context: Context) -> Iterator[Signal]:
    """The current spend rate against what the month's budget allows per day.

    Rates rather than totals, because a budget compared with month-to-date spend calls
    every month behind until its last day. The rate comes from the detection window and
    not from the whole month: a month-to-date average is held down by the days before
    the overspend began, so it crosses the budget line a week or more after the spending
    changed. The projection FR-7 reports to the operator is in ``pacing.py``.
    """
    spend = _grouped(ads, _CHANNEL_KEY, recent)
    for channel, budget in context.month_budgets.items():
        measures = spend.get(channel)
        if measures is None or budget <= 0:
            continue
        signal = detectors.goal_breach(
            _channel_entity(channel),
            "spend",
            Window(recent, measures),
            budget / days_in_month(context.as_of),
            prefer_higher=False,
        )
        if signal is not None:
            yield signal


def _tracking_signals(ads: pd.DataFrame, recent: Period, context: Context) -> Iterator[Signal]:
    spend = _grouped(ads, _CHANNEL_KEY, recent)
    for channel, check in context.tracking.items():
        signal = detectors.tracking_break(
            _channel_entity(channel), check, Window(recent, spend.get(channel, {}))
        )
        if signal is not None:
            yield signal
