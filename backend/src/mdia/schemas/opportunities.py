"""API DTOs for opportunities (``/opportunities``).

Numbers go out raw and metrics go out as their keys: the front end owns ₹ and %
formatting (UI.md §6). Words that carry meaning — the title, the observation, the cause
label — are produced in ``domain/`` and only passed through here.
"""

from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, ConfigDict, Field

from mdia.domain.diagnosis import Cause
from mdia.domain.kpi import Metric
from mdia.domain.opportunities import OpportunityKind
from mdia.domain.recommendations import Action, Band, Risk
from mdia.domain.trust import TrustStatus
from mdia.models.analysis import DiagnosisSource, OpportunityStatus
from mdia.schemas.metrics import PeriodOut

# A dismissal reason is short but never empty: it is the decision log's entry (FR-10.2).
REASON_MIN = 3
REASON_MAX = 500


class _Out(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class EntityOut(_Out):
    level: str
    key: str
    name: str
    channel: str | None = None


class SignalOut(_Out):
    """One movement behind the opportunity, as the "Signals" section lists them."""

    id: str
    detector: str
    metric: Metric
    entity: EntityOut
    window: PeriodOut
    current: float | None
    baseline: float | None
    change_pct: float | None
    adverse: bool
    impact: float
    score: float


class NodeOut(_Out):
    """One metric in the evidence tree, with its share of the change above it."""

    metric: Metric
    before: float | None
    after: float | None
    change_pct: float | None
    share_pct: float | None
    # Whether a rise in this metric is good news; ``None`` for a base measure like spend.
    higher_is_better: bool | None
    children: list[NodeOut] = []


class HypothesisOut(_Out):
    cause: Cause
    cause_label: str
    statement: str
    signal_ids: list[str]


class RecommendationOut(_Out):
    action: Action
    rationale: str
    # The rupees this could recover, low to high; computed, never from the LLM.
    expected_impact: tuple[float, float]
    confidence: float
    risk: Risk
    watch: Metric
    stop_condition: str
    params: dict[str, str]


class OpportunityOut(_Out):
    """A list row: priority dot, title, channel, impact, confidence and age."""

    id: int
    key: str
    kind: OpportunityKind
    status: OpportunityStatus
    title: str
    entity_level: str
    entity_key: str
    entity_name: str
    channel_id: str | None
    window: PeriodOut
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
    age_days: int
    signal_count: int
    cause: Cause | None
    cause_label: str | None
    observation: str | None
    diagnosis_source: DiagnosisSource | None
    dismissed_reason: str | None


class OpportunityListOut(_Out):
    opportunities: list[OpportunityOut]


class OpportunityDetailOut(_Out):
    """The four sections of UI.md §5.2, in that order, plus the signals behind them."""

    summary: OpportunityOut
    tree: NodeOut | None
    hypotheses: list[HypothesisOut]
    alternatives: list[str]
    recommendation: RecommendationOut | None
    signals: list[SignalOut]
    trust: TrustStatus
    protected: bool
    # Whether the words came from the LLM through the grounding guard (FR-8.3).
    grounded: bool


class DismissIn(BaseModel):
    """Why this is being set aside; it goes to the decision log."""

    reason: str = Field(min_length=REASON_MIN, max_length=REASON_MAX)
