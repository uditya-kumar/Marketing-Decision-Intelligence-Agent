"""Opportunities for the UI (FR-6.4, FR-8, FR-9): read the stored analysis, dismiss one.

Nothing is recomputed here. The run already wrote the evidence, the diagnosis and the
recommendation, so this service only reshapes them into the four sections the detail
page shows — what happened, why, likely cause, recommended — and the row the list shows.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast

from mdia.core.errors import NotFoundError
from mdia.domain.diagnosis import CAUSE_LABELS
from mdia.domain.kpi import higher_is_better
from mdia.domain.periods import Period
from mdia.domain.recommendations import band
from mdia.domain.wording import title
from mdia.repositories.analysis import AnalysisRepository
from mdia.repositories.decisions import DecisionRepository

if TYPE_CHECKING:
    import datetime as dt
    from collections.abc import Collection, Sequence
    from decimal import Decimal

    from sqlalchemy.orm import Session

    from mdia.domain.diagnosis import Cause
    from mdia.domain.kpi import Metric
    from mdia.domain.opportunities import OpportunityKind
    from mdia.domain.recommendations import Band
    from mdia.domain.trust import TrustStatus
    from mdia.models import Opportunity
    from mdia.models.analysis import DiagnosisSource, OpportunityStatus

# The list is ranked, so more than this is scrolling past things that do not matter.
LIST_LIMIT = 50
# How many of each kind the Today screen carries (UI.md §5.1).
TODAY_LIMIT = 3


@dataclass(frozen=True, slots=True)
class OpportunitySummary:
    """One list row, and the head of the detail page."""

    id: int
    key: str
    kind: OpportunityKind
    status: OpportunityStatus
    # What it means in plain words, from the entity and the metric that moved.
    title: str
    entity_level: str
    entity_key: str
    entity_name: str
    channel_id: str | None
    window: Period
    # The day the problem was first detected, which is what "detected 14 Oct" reads off.
    first_seen: dt.date
    primary_metric: Metric
    primary_detector: str
    current: float | None
    baseline: float | None
    change_pct: float | None
    impact: float
    confidence: float | None
    priority: float | None
    band: Band
    # Days since the problem was first detected, for "this has been going on a while".
    age_days: int
    signal_count: int
    cause: Cause | None
    cause_label: str | None
    # What happened, in one computed sentence.
    observation: str | None
    diagnosis_source: DiagnosisSource | None
    dismissed_reason: str | None


@dataclass(frozen=True, slots=True)
class OpportunityDetail:
    """The detail page, in the order UI.md §5.2 fixes: what happened → why → cause → action."""

    summary: OpportunitySummary
    # Why, arithmetically: the metric that moved, split into its drivers.
    tree: dict[str, Any] | None
    hypotheses: list[dict[str, Any]]
    alternatives: list[str]
    recommendation: dict[str, Any] | None
    signals: list[dict[str, Any]]
    trust: TrustStatus
    protected: bool
    grounded: bool


class OpportunityService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._analysis = AnalysisRepository(session)
        self._decisions = DecisionRepository(session)

    def find(
        self,
        *,
        status: Collection[OpportunityStatus] | None = None,
        kind: OpportunityKind | None = None,
        limit: int = LIST_LIMIT,
    ) -> list[OpportunitySummary]:
        rows = self._analysis.list(status=status, kind=kind, limit=limit)
        return [summary(row) for row in rows]

    def top(self, kind: OpportunityKind, limit: int = TODAY_LIMIT) -> list[OpportunitySummary]:
        """The most urgent ones of a kind still awaiting a decision, for the Today screen.

        One being tested has had its decision, and Today's experiments strip carries it.
        """
        awaiting: tuple[OpportunityStatus] = ("open",)
        return self.find(status=awaiting, kind=kind, limit=limit)

    def get(self, opportunity_id: int) -> OpportunityDetail:
        row = self._require(opportunity_id)
        evidence = row.evidence or {}
        diagnosis = row.diagnosis or {}
        tree = evidence.get("tree")
        return OpportunityDetail(
            summary=summary(row),
            tree=None if tree is None else _node(tree),
            hypotheses=[_hypothesis(item) for item in diagnosis.get("hypotheses") or []],
            alternatives=diagnosis.get("alternatives") or [],
            recommendation=row.recommendation,
            signals=list(row.signals or []),
            trust=cast("TrustStatus", evidence.get("trust", "ok")),
            protected=bool(evidence.get("protected")),
            grounded=row.diagnosis_source == "llm",
        )

    def dismiss(self, opportunity_id: int, reason: str) -> OpportunitySummary:
        """Set it aside with a reason; the next run will not reopen it (FR-10.2).

        A dismissal is a decision like any other, so it joins the log even though it
        proposes no change (FR-10.4).
        """
        row = self._require(opportunity_id)
        self._analysis.dismiss(opportunity_id, reason)
        self._decisions.log(
            "dismiss", opportunity_id=opportunity_id, reason=reason, impact=row.impact
        )
        self._session.commit()
        return summary(self._require(opportunity_id))

    def _require(self, opportunity_id: int) -> Opportunity:
        row = self._analysis.get(opportunity_id)
        if row is None:
            raise NotFoundError(f"No opportunity {opportunity_id}.")
        return row


def summary(row: Opportunity) -> OpportunitySummary:
    """One stored opportunity as the list row and the head of the detail page."""
    kind = cast("OpportunityKind", row.kind)
    metric = cast("Metric", row.primary_metric)
    diagnosis = row.diagnosis or {}
    cause = _cause(diagnosis)
    priority = _float(row.priority)
    return OpportunitySummary(
        id=row.id,
        key=row.key,
        kind=kind,
        status=row.status,
        title=title(row.entity_name, metric, kind=kind),
        entity_level=row.entity_level,
        entity_key=row.entity_key,
        entity_name=row.entity_name,
        channel_id=row.channel_id,
        window=Period(row.window_start, row.window_end),
        first_seen=row.first_seen_date,
        primary_metric=metric,
        primary_detector=row.primary_detector,
        current=_value(row.signals, "current"),
        baseline=_value(row.signals, "baseline"),
        change_pct=_value(row.signals, "change_pct"),
        impact=float(row.impact),
        confidence=_float(row.confidence),
        priority=priority,
        band=band(priority),
        age_days=_age(row.first_seen_date, row.last_seen_date),
        signal_count=len(row.signals or []),
        cause=cause,
        cause_label=None if cause is None else CAUSE_LABELS[cause],
        observation=diagnosis.get("observation"),
        diagnosis_source=row.diagnosis_source,
        dismissed_reason=row.dismissed_reason,
    )


def _hypothesis(stored: dict[str, Any]) -> dict[str, Any]:
    """A stored hypothesis with its cause spelled out for the reader."""
    cause = cast("Cause", stored["cause"])
    return {**stored, "cause_label": CAUSE_LABELS[cause]}


def _node(stored: dict[str, Any]) -> dict[str, Any]:
    """A stored tree node with its metric's direction, so the UI knows which way is good."""
    metric = cast("Metric", stored["metric"])
    return {
        **stored,
        "higher_is_better": higher_is_better(metric),
        "children": [_node(child) for child in stored.get("children") or []],
    }


def _cause(diagnosis: dict[str, Any]) -> Cause | None:
    """The leading hypothesis' cause; the rest are on the detail page."""
    hypotheses = diagnosis.get("hypotheses") or []
    return cast("Cause", hypotheses[0]["cause"]) if hypotheses else None


def _value(signals: Sequence[dict[str, Any]] | None, field: str) -> float | None:
    """A number off the primary signal, which is stored first (strongest score)."""
    if not signals:
        return None
    value = signals[0].get(field)
    return None if value is None else float(value)


def _age(first_seen: dt.date, last_seen: dt.date) -> int:
    return (last_seen - first_seen).days


def _float(value: Decimal | float | None) -> float | None:
    return None if value is None else float(value)
