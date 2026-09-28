"""One week's report payload, for the payload tests and the narration graph (task 9.1)."""

from __future__ import annotations

import datetime as dt

from mdia.domain.pacing import pace
from mdia.domain.periods import trailing
from mdia.domain.reports import (
    DecisionLine,
    ExperimentLine,
    KpiLine,
    OpportunityLine,
    PacingLine,
    WeeklyPayload,
    build,
)

WEEK = trailing(dt.date(2026, 10, 22), 7)


def report_kpi(
    metric: str = "store_revenue",
    value: float | None = 1_640_000.0,
    *,
    previous: float | None = 2_080_000.0,
    change_pct: float | None = -21.2,
    target: float | None = 1_870_000.0,
    goal_status: str | None = "behind",
    reliable: bool = True,
) -> KpiLine:
    return KpiLine(
        metric=metric,  # type: ignore[arg-type]
        value=value,
        previous=previous,
        change_pct=change_pct,
        target=target,
        goal_status=goal_status,  # type: ignore[arg-type]
        reliable=reliable,
    )


def report_pacing(budget: float = 600_000.0, spent: float = 430_000.0) -> PacingLine:
    return PacingLine(label="Meta", pacing=pace(budget, spent, WEEK.end))


def report_opportunity(
    ident: int = 1,
    kind: str = "issue",
    *,
    band: str = "high",
    impact: float = 84_000.0,
    metric: str = "cpa",
    current: float | None = 612.4,
    baseline: float | None = 420.0,
) -> OpportunityLine:
    return OpportunityLine(
        id=ident,
        kind=kind,  # type: ignore[arg-type]
        band=band,  # type: ignore[arg-type]
        title="Retargeting costs more per sale",
        entity="Retargeting — Broad",
        metric=metric,  # type: ignore[arg-type]
        current=current,
        baseline=baseline,
        change_pct=45.8,
        impact=impact,
        confidence=0.72,
        cause="creative_fatigue",  # type: ignore[arg-type]
    )


def report_experiment(verdict: str | None = "worked") -> ExperimentLine:
    return ExperimentLine(
        title="Rotate the retargeting creative",
        action="rotate_creative",
        metric="cpa",
        verdict=verdict,  # type: ignore[arg-type]
        before=612.4,
        after=438.0,
        sample_days=7,
    )


def report_decision(kind: str = "approve", reason: str | None = None) -> DecisionLine:
    return DecisionLine(
        kind=kind,
        title="Rotate the retargeting creative",
        action="rotate_creative",
        reason=reason,
    )


def weekly_payload(**overrides: object) -> WeeklyPayload:
    """A week with one of everything; pass a field to leave it out or widen it."""
    fields: dict[str, object] = {
        "kpis": [report_kpi(), report_kpi("cpa", 612.4, target=None, goal_status=None)],
        "pacing": [report_pacing()],
        "opportunities": [report_opportunity(), report_opportunity(2, "win", impact=36_000.0)],
        "decisions": [report_decision()],
        "experiments": [report_experiment()],
    }
    fields.update(overrides)
    return build(WEEK, **fields)  # type: ignore[arg-type]
