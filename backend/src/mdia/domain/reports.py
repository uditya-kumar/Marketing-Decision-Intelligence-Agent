"""The weekly report's payload (FR-11.1): every number the report may contain.

The payload is built entirely in code — KPIs against goals, week-on-week, pacing, the
opportunities that mattered, the decisions taken and how the experiments turned out.
The model that narrates it later gets this and nothing else, and
:func:`quotable` is the set of numbers its prose is then checked against (FR-11.2).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from mdia.domain.wording import as_shown

if TYPE_CHECKING:
    from collections.abc import Sequence

    from mdia.domain.diagnosis import Cause
    from mdia.domain.experiments import Verdict
    from mdia.domain.goals import GoalStatus
    from mdia.domain.kpi import Metric
    from mdia.domain.opportunities import OpportunityKind
    from mdia.domain.pacing import Pacing
    from mdia.domain.periods import Period
    from mdia.domain.recommendations import Action, Band

# The report is a page, not a list: only the few rows a reader will act on.
TOP_OPPORTUNITIES = 5
MAX_DECISIONS = 8


@dataclass(frozen=True, slots=True)
class KpiLine:
    """One headline KPI: where it is, where it was, and what it was aiming at."""

    metric: Metric
    value: float | None
    previous: float | None
    change_pct: float | None
    target: float | None
    goal_status: GoalStatus | None
    # False when the metric rests on data that failed a trust check (FR-5).
    reliable: bool


@dataclass(frozen=True, slots=True)
class PacingLine:
    label: str
    pacing: Pacing


@dataclass(frozen=True, slots=True)
class OpportunityLine:
    id: int
    kind: OpportunityKind
    band: Band
    title: str
    entity: str
    metric: Metric
    current: float | None
    baseline: float | None
    change_pct: float | None
    impact: float
    confidence: float | None
    cause: Cause | None


@dataclass(frozen=True, slots=True)
class DecisionLine:
    kind: str
    title: str
    action: Action | None
    reason: str | None


@dataclass(frozen=True, slots=True)
class ExperimentLine:
    title: str
    action: Action
    metric: Metric
    verdict: Verdict | None
    before: float | None
    after: float | None
    sample_days: int | None


@dataclass(frozen=True, slots=True)
class WeeklyPayload:
    """The whole report as computed facts, ready to be stored and narrated."""

    week: Period
    kpis: list[KpiLine]
    pacing: list[PacingLine]
    opportunities: list[OpportunityLine]
    decisions: list[DecisionLine]
    experiments: list[ExperimentLine]
    # Totals the narrative leads on, summed here so nobody re-adds them downstream.
    issue_cost: float
    win_upside: float
    worked: int
    trust_warning: bool


def build(
    week: Period,
    *,
    kpis: Sequence[KpiLine],
    pacing: Sequence[PacingLine],
    opportunities: Sequence[OpportunityLine],
    decisions: Sequence[DecisionLine],
    experiments: Sequence[ExperimentLine],
) -> WeeklyPayload:
    """Assemble the week: the rows worth printing, and the totals over all of them."""
    issues = [row for row in opportunities if row.kind == "issue"]
    wins = [row for row in opportunities if row.kind == "win"]
    return WeeklyPayload(
        week=week,
        kpis=list(kpis),
        pacing=list(pacing),
        opportunities=[*issues[:TOP_OPPORTUNITIES], *wins[:TOP_OPPORTUNITIES]],
        decisions=list(decisions[:MAX_DECISIONS]),
        experiments=list(experiments),
        issue_cost=sum(abs(row.impact) for row in issues),
        win_upside=sum(abs(row.impact) for row in wins),
        worked=sum(1 for row in experiments if row.verdict == "worked"),
        trust_warning=any(not line.reliable for line in kpis),
    )


def quotable(payload: WeeklyPayload) -> set[float]:
    """Every number the narrative is allowed to use, as a reader would see it."""
    found: set[float] = {float(payload.week.days), payload.issue_cost, payload.win_upside}
    # Counting the report's own rows is fair: "two of the three changes worked".
    for rows in (payload.kpis, payload.opportunities, payload.decisions, payload.experiments):
        found.update(float(count) for count in range(len(rows) + 1))
    found.add(float(payload.worked))
    for kpi in payload.kpis:
        found.update(_shown(kpi.metric, (kpi.value, kpi.previous, kpi.target)))
        if kpi.change_pct is not None:
            found.add(kpi.change_pct)
    for budget in payload.pacing:
        pace = budget.pacing
        found.update(
            {
                pace.budget,
                pace.spent,
                pace.spent_pct,
                pace.remaining_budget,
                pace.month_elapsed_pct,
                pace.projected,
                pace.daily_run_rate,
            }
        )
        if pace.suggested_daily is not None:
            found.add(pace.suggested_daily)
    for row in payload.opportunities:
        found.update(_shown(row.metric, (row.current, row.baseline)))
        found.add(abs(row.impact))
        if row.change_pct is not None:
            found.add(row.change_pct)
        if row.confidence is not None:
            found.update({row.confidence, row.confidence * 100})
    for run in payload.experiments:
        found.update(_shown(run.metric, (run.before, run.after)))
        if run.sample_days is not None:
            found.add(float(run.sample_days))
    end = payload.week.end
    found.update({float(end.day), float(end.month), float(end.year)})
    found.update({float(payload.week.start.day), float(payload.week.start.month)})
    # "₹16.40 L" is one claim but two numbers to a reader, so the mantissa counts as quoted.
    found.update(
        value / scale for value in tuple(found) for scale in (1e5, 1e7) if abs(value) >= scale
    )
    return {abs(value) for value in found}


def _shown(metric: Metric, values: Sequence[float | None]) -> set[float]:
    """A value counts as quoted either as it is or as a reader sees it (7.24%, not 0.0724)."""
    return {
        number
        for value in values
        if value is not None
        for number in (value, as_shown(metric, value))
    }
