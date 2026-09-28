"""Experiments (FR-10): what a change is meant to achieve, and whether it did.

Both halves are arithmetic. The plan reads its target off the metric's own direction,
and the verdict is a before-versus-after comparison with a floor under the sample and
under the effect, so "worked" never means "moved a little". The LLM has no part in
either: it cannot pick the action, the target or the verdict.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from mdia.domain.kpi import change_pct, higher_is_better, label
from mdia.domain.periods import Period
from mdia.domain.wording import value_text

if TYPE_CHECKING:
    from mdia.domain.kpi import Metric
    from mdia.domain.recommendations import Action

Verdict = Literal["worked", "did_not_work", "inconclusive"]

# A week of data is the detection window, so it is also the natural test length.
DEFAULT_DURATION_DAYS = 7
# Fewer days than this cannot answer the question, however good the numbers look.
MIN_SAMPLE_DAYS = 5
# A move smaller than this is inside the noise these windows carry (see signals.py).
MIN_EFFECT_PCT = 5.0

# How each action reads at the start of a hypothesis. The catalogue is FR-9.1's.
_GERUNDS: dict[Action, str] = {
    "pause_creative": "Pausing this creative",
    "rotate_creative": "Rotating in a fresh creative",
    "refine_audience": "Narrowing the audience",
    "investigate_landing_page": "Fixing what the landing page check turns up",
    "fix_tracking": "Repairing the conversion tracking",
    "shift_budget": "Moving budget",
    "adjust_pacing": "Adjusting the daily spend",
}


@dataclass(frozen=True, slots=True)
class Plan:
    """The auto-filled experiment of FR-10.1, ready for someone to approve."""

    action: Action
    hypothesis: str
    metric: Metric
    # Where the metric stands now, and where the change should take it.
    baseline: float | None
    target: float | None
    duration_days: int


@dataclass(frozen=True, slots=True)
class Progress:
    """How far a running experiment has got, for "day 3/7"."""

    day: int
    total: int
    due: bool


def target(metric: Metric, *, baseline: float | None, reference: float | None) -> float | None:
    """Where the metric should get to: the better of where it is and where it was.

    For a problem that is the level before it broke; for a win it is the level the
    winning segment is already at, which is what spending more should preserve.
    """
    if baseline is None:
        return reference
    if reference is None:
        # Nothing to aim at: a target equal to today's level would be met by standing still.
        return None
    better = higher_is_better(metric)
    if better is None:
        return reference
    return max(baseline, reference) if better else min(baseline, reference)


def hypothesis(
    action: Action,
    metric: Metric,
    *,
    entity_name: str,
    baseline: float | None,
    goal: float | None,
    duration_days: int,
) -> str:
    """The sentence the experiment is judged against, in the numbers it will be judged on."""
    opening = f"{_GERUNDS[action]} on {entity_name}"
    within = f"within {duration_days} days"
    if baseline is None or goal is None:
        return f"{opening} should improve {label(metric)} {within}."
    return (
        f"{opening} should move {label(metric)} from {value_text(metric, baseline)}"
        f" to {value_text(metric, goal)} {within}."
    )


def plan(
    action: Action,
    metric: Metric,
    *,
    entity_name: str,
    current: float | None,
    reference: float | None,
    duration_days: int = DEFAULT_DURATION_DAYS,
) -> Plan:
    """Fill in an experiment from the recommendation and the movement behind it."""
    goal = target(metric, baseline=current, reference=reference)
    return Plan(
        action=action,
        hypothesis=hypothesis(
            action,
            metric,
            entity_name=entity_name,
            baseline=current,
            goal=goal,
            duration_days=duration_days,
        ),
        metric=metric,
        baseline=current,
        target=goal,
        duration_days=duration_days,
    )


def window(started_on: dt.date, duration_days: int) -> Period:
    """The days the change is judged over, starting the day after it was approved."""
    start = started_on + dt.timedelta(days=1)
    return Period(start, start + dt.timedelta(days=duration_days - 1))


def improvement_pct(metric: Metric, *, before: float | None, after: float | None) -> float | None:
    """How far the metric moved in the direction that counts as better, in per cent.

    ``None`` when there is nothing to compare, or when the metric has no direction:
    spend going up is neither good nor bad on its own.
    """
    change = change_pct(before, after)
    better = higher_is_better(metric)
    if change is None or better is None:
        return None
    return change if better else -change


def verdict(
    metric: Metric, *, before: float | None, after: float | None, sample_days: int
) -> Verdict:
    """FR-10.3: before versus after, inconclusive unless the data can carry a verdict."""
    if sample_days < MIN_SAMPLE_DAYS:
        return "inconclusive"
    gain = improvement_pct(metric, before=before, after=after)
    if gain is None or abs(gain) < MIN_EFFECT_PCT:
        return "inconclusive"
    return "worked" if gain > 0 else "did_not_work"


def progress(*, started_on: dt.date, ends_on: dt.date, as_of: dt.date) -> Progress:
    """Days elapsed out of the duration, clamped to it, and whether it is ready to judge."""
    total = (ends_on - started_on).days
    day = max(0, min(total, (as_of - started_on).days))
    return Progress(day=day, total=total, due=as_of >= ends_on)
