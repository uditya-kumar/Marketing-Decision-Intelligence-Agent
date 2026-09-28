"""The week's views as the report's payload, and the payload as a database row.

Every screen already has a shape for its numbers, so the report reuses them rather than
querying again: this is the one place those view objects become
:class:`~mdia.domain.reports.WeeklyPayload` lines. No number is computed here.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import asdict
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from mdia.domain.reports import (
    DecisionLine,
    ExperimentLine,
    KpiLine,
    OpportunityLine,
    PacingLine,
    build,
)
from mdia.domain.sources import SOURCE_LABELS

if TYPE_CHECKING:
    from collections.abc import Sequence

    from mdia.agents.report import Report
    from mdia.domain.periods import Period
    from mdia.domain.reports import WeeklyPayload
    from mdia.services.decisions import DecisionView
    from mdia.services.experiment_rows import ExperimentView
    from mdia.services.metrics import KpiSummary
    from mdia.services.opportunities import OpportunitySummary
    from mdia.services.pacing import PacingView

ALL_CHANNELS = "All channels"


def payload_for(
    week: Period,
    *,
    kpis: Sequence[KpiSummary],
    pacing: PacingView,
    opportunities: Sequence[OpportunitySummary],
    decisions: Sequence[DecisionView],
    experiments: Sequence[ExperimentView],
) -> WeeklyPayload:
    """One week's facts, gathered from the same views the screens read."""
    return build(
        week,
        kpis=[_kpi(row) for row in kpis],
        pacing=_pacing(pacing),
        opportunities=[_opportunity(row) for row in opportunities],
        decisions=[_decision(row) for row in decisions],
        experiments=[_experiment(row) for row in experiments],
    )


def report_row(payload: WeeklyPayload, report: Report) -> dict[str, Any]:
    """The upsert payload for one week, keyed on the week it covers."""
    return {
        "week_start": payload.week.start,
        "week_end": payload.week.end,
        "payload": _jsonable(asdict(payload)),
        "narrative": {"summary": report.text.summary, "detail": report.text.detail},
        "source": report.source,
        "grounded": report.grounded,
    }


def _kpi(row: KpiSummary) -> KpiLine:
    return KpiLine(
        metric=row.metric,
        value=row.value,
        previous=row.previous,
        change_pct=row.change_pct,
        target=None if row.goal is None else row.goal.target,
        goal_status=None if row.goal is None else row.goal.status,
        reliable=row.reliable,
    )


def _pacing(view: PacingView) -> list[PacingLine]:
    """Every channel with a budget, and the total when more than one has one."""
    lines = [PacingLine(SOURCE_LABELS[row.channel], row.pacing) for row in view.channels]
    if view.total is not None and len(lines) > 1:
        lines.append(PacingLine(ALL_CHANNELS, view.total))
    return lines


def _opportunity(row: OpportunitySummary) -> OpportunityLine:
    return OpportunityLine(
        id=row.id,
        kind=row.kind,
        band=row.band,
        title=row.title,
        entity=row.entity_name,
        metric=row.primary_metric,
        current=row.current,
        baseline=row.baseline,
        change_pct=row.change_pct,
        impact=row.impact,
        confidence=row.confidence,
        cause=row.cause,
    )


def _decision(row: DecisionView) -> DecisionLine:
    return DecisionLine(
        kind=row.kind,
        title=row.opportunity.title,
        action=None if row.experiment is None else row.experiment.action,
        reason=row.reason,
    )


def _experiment(row: ExperimentView) -> ExperimentLine:
    return ExperimentLine(
        title=row.opportunity.title,
        action=row.action,
        metric=row.metric,
        verdict=row.verdict,
        before=row.before,
        after=row.after,
        sample_days=row.sample_days,
    )


def _jsonable(value: Any) -> Any:
    """Dates and decimals as JSON, for the payload column."""
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, dt.date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return value
