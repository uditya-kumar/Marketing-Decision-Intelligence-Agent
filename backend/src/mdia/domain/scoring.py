"""Scoring and suppression (FR-6.2): which signals are worth a marketer's attention.

The score is ``|Δ| × ₹ impact``, so a small move on a large budget outranks a
dramatic one on a campaign spending nothing. Suppression comes first: a festive
spike is the season doing its job, and a conversion a broken pixel never reported
is not a conversion anyone lost.
"""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from mdia.domain.kpi import definition

if TYPE_CHECKING:
    from collections.abc import Collection, Iterable, Sequence

    from mdia.domain.kpi import Metric
    from mdia.domain.periods import Period
    from mdia.domain.signals import Signal
    from mdia.domain.sources import Channel

# Below this the movement is real but not worth anyone's morning (tuned in evaluation).
MIN_SCORE = 5_000.0
# Detectors whose finding is not a statistical movement, so the score threshold would be
# the wrong filter for them: a broken pixel matters however little money rides on it, and
# a target or budget the operator set is a commitment whose own tolerance is the threshold.
_UNCONDITIONAL: frozenset[str] = frozenset({"tracking_break", "goal_breach"})
# A 900 % jump on a tiny budget shouldn't outrank a 20 % slide on a big one.
MAX_CHANGE_PCT = 100.0

# Metrics that are rupees per unit of something: the units turn a delta into rupees.
_MONEY_UNITS: dict[Metric, tuple[str, float]] = {
    "roas": ("spend", 1.0),
    "mer": ("spend", 1.0),
    "cpa": ("platform_conversions", 1.0),
    "aov": ("platform_conversions", 1.0),
    "store_aov": ("store_orders", 1.0),
    "cpc": ("clicks", 1.0),
    "cpm": ("impressions", 0.001),
}
# Metrics that are already rupees; their delta is a daily rate.
_MONEY_MEASURES: frozenset[str] = frozenset({"spend", "platform_revenue", "store_revenue"})
# What a broken pixel stops reporting; impressions, clicks and spend keep arriving.
_TRACKED_MEASURES: frozenset[str] = frozenset({"platform_conversions", "platform_revenue"})


def needs_tracking(metric: Metric) -> bool:
    """Whether the metric is built on platform-reported conversions."""
    kpi = definition(metric)
    if kpi is None:
        return metric in _TRACKED_MEASURES
    return kpi.numerator in _TRACKED_MEASURES or kpi.denominator in _TRACKED_MEASURES


def rupee_impact(signal: Signal) -> float:
    """What the movement is worth over the window, in rupees.

    Exact where the metric is rupees per unit (a ₹40 CPA rise over 500 conversions is
    ₹20,000). A pure rate such as CTR or a funnel step has no such conversion, so what
    is at stake is the spend riding on it, which ``score`` then scales by how far the
    rate moved. Scaling it here as well would square the movement and hide a small
    shift in a rate that a whole channel's budget depends on.
    """
    if signal.current is None or signal.baseline is None or signal.change_pct is None:
        return 0.0
    delta = abs(signal.current - signal.baseline)
    if signal.metric in _MONEY_UNITS:
        column, scale = _MONEY_UNITS[signal.metric]
        return delta * (signal.measures.get(column) or 0.0) * scale
    if signal.metric in _MONEY_MEASURES:
        return delta * signal.window.days
    at_stake = signal.measures.get("spend") or 0.0
    return at_stake


def score(change_pct: float | None, impact: float) -> float:
    if change_pct is None:
        return 0.0
    return min(abs(change_pct), MAX_CHANGE_PCT) / 100 * impact


def is_suppressed(
    signal: Signal,
    *,
    festive: Sequence[Period] = (),
    broken: Collection[Channel] = (),
) -> bool:
    """Whether the signal should never be shown, whatever it scores."""
    # The tracking break itself is the one thing worth saying about a broken channel.
    if signal.detector == "tracking_break":
        return False
    if needs_tracking(signal.metric):
        channel = signal.entity.channel
        # A blended metric rides on every channel's conversions, so any break taints it.
        if bool(broken) if channel is None else channel in broken:
            return True
    return any(signal.window.overlaps(window) for window in festive)


def rank(
    signals: Iterable[Signal],
    *,
    festive: Sequence[Period] = (),
    broken: Collection[Channel] = (),
    min_score: float = MIN_SCORE,
) -> list[Signal]:
    """Suppress, score, drop what's below the threshold, and order by score."""
    kept = []
    for signal in signals:
        if is_suppressed(signal, festive=festive, broken=broken):
            continue
        impact = rupee_impact(signal)
        value = score(signal.change_pct, impact)
        if value < min_score and signal.detector not in _UNCONDITIONAL:
            continue
        kept.append(replace(signal, impact=impact, score=value))
    return sorted(kept, key=lambda signal: signal.score, reverse=True)
