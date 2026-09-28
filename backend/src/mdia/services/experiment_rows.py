"""Translation between the ``experiments`` table and the rest of the app.

One way in — the draft a recommendation implies (FR-10.1) — and one way out: the view
every screen reads. Both are shaping only; the target, the hypothesis wording and the
progress all come from ``domain/experiments.py``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast

from mdia.core.errors import ValidationError
from mdia.domain.experiments import DEFAULT_DURATION_DAYS, plan, progress
from mdia.domain.recommendations import ACTION_TYPES
from mdia.services.opportunities import summary

if TYPE_CHECKING:
    import datetime as dt
    from collections.abc import Sequence
    from decimal import Decimal

    from mdia.domain.experiments import Progress, Verdict
    from mdia.domain.kpi import Metric
    from mdia.domain.recommendations import Action
    from mdia.models import Experiment, Opportunity
    from mdia.models.experiments import ExperimentStatus
    from mdia.services.opportunities import OpportunitySummary

# Today has room for a line, not a list; the Experiments page has the rest (UI.md §5.1).
TODAY_LIMIT = 2


@dataclass(frozen=True, slots=True)
class ExperimentView:
    """One experiment as every screen shows it, with the opportunity it came from."""

    id: int
    status: ExperimentStatus
    action: Action
    hypothesis: str
    metric: Metric
    baseline: float | None
    target: float | None
    duration_days: int
    started_on: dt.date | None
    ends_on: dt.date | None
    # Only while it is running: "day 3/7".
    progress: Progress | None
    verdict: Verdict | None
    before: float | None
    after: float | None
    sample_days: int | None
    evaluated_on: dt.date | None
    reason: str | None
    opportunity: OpportunitySummary


@dataclass(frozen=True, slots=True)
class ExperimentsToday:
    """The Today strip of UI.md §5.1: what is running, what came back, what is waiting."""

    running: list[ExperimentView]
    completed: list[ExperimentView]
    awaiting: int


def group_today(views: Sequence[ExperimentView]) -> ExperimentsToday:
    """The few experiments Today has room for, newest first, plus the drafts' count."""
    return ExperimentsToday(
        running=[view for view in views if view.status == "running"][:TODAY_LIMIT],
        completed=[view for view in views if view.status == "completed"][:TODAY_LIMIT],
        awaiting=sum(1 for view in views if view.status == "draft"),
    )


def draft_row(opportunity: Opportunity) -> dict[str, Any]:
    """The experiment this opportunity's recommendation implies, ready to be stored."""
    recommendation = opportunity.recommendation or {}
    action = recommendation.get("action")
    if action not in ACTION_TYPES:
        raise ValidationError("This opportunity has no recommended action to test.")
    metric = cast("Metric", recommendation.get("watch") or opportunity.primary_metric)
    # The action may ask for a different metric than the one that raised the opportunity;
    # when it does, the signal's levels are not the before-and-after for it.
    signal = (opportunity.signals or [{}])[0] if metric == opportunity.primary_metric else {}
    filled = plan(
        cast("Action", action),
        metric,
        entity_name=opportunity.entity_name,
        current=_signal_value(signal, "current"),
        reference=_signal_value(signal, "baseline"),
        duration_days=DEFAULT_DURATION_DAYS,
    )
    return {
        "opportunity_id": opportunity.id,
        "action": filled.action,
        "hypothesis": filled.hypothesis,
        "metric": filled.metric,
        "baseline": filled.baseline,
        "target": filled.target,
        "duration_days": filled.duration_days,
        "status": "draft",
    }


def view(row: Experiment, opportunity: Opportunity, as_of: dt.date | None) -> ExperimentView:
    return ExperimentView(
        id=row.id,
        status=row.status,
        action=cast("Action", row.action),
        hypothesis=row.hypothesis,
        metric=cast("Metric", row.metric),
        baseline=_float(row.baseline),
        target=_float(row.target),
        duration_days=row.duration_days,
        started_on=row.started_on,
        ends_on=row.ends_on,
        progress=_progress(row, as_of),
        verdict=row.verdict,
        before=_float(row.before_value),
        after=_float(row.after_value),
        sample_days=row.sample_days,
        evaluated_on=row.evaluated_on,
        reason=row.reason,
        opportunity=summary(opportunity),
    )


def _signal_value(signal: dict[str, Any], field: str) -> float | None:
    value = signal.get(field)
    return None if value is None else float(value)


def _progress(row: Experiment, as_of: dt.date | None) -> Progress | None:
    if row.status != "running" or row.started_on is None or row.ends_on is None or as_of is None:
        return None
    return progress(started_on=row.started_on, ends_on=row.ends_on, as_of=as_of)


def _float(value: Decimal | float | None) -> float | None:
    return None if value is None else float(value)
