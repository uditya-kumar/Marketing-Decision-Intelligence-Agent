"""API DTOs for experiments (``/experiments``).

Numbers go out raw, as everywhere else; the hypothesis is the only sentence here and it
is composed in ``domain/experiments.py``, never by the LLM.
"""

from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, ConfigDict, Field

from mdia.domain.kpi import Metric
from mdia.domain.recommendations import Action
from mdia.models.experiments import ExperimentStatus, ExperimentVerdict
from mdia.schemas.opportunities import REASON_MAX, REASON_MIN, OpportunityOut


class _Out(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ProgressOut(_Out):
    """How far a running experiment has got: "day 3/7"."""

    day: int
    total: int
    due: bool


class ExperimentOut(_Out):
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
    progress: ProgressOut | None
    verdict: ExperimentVerdict | None
    before: float | None
    after: float | None
    sample_days: int | None
    evaluated_on: dt.date | None
    reason: str | None
    opportunity: OpportunityOut


class ExperimentListOut(_Out):
    experiments: list[ExperimentOut]


class DraftIn(BaseModel):
    """Which opportunity's recommendation to turn into an experiment (FR-10.1)."""

    opportunity_id: int


class DecideIn(BaseModel):
    """An optional note on an approval or rejection; it goes to the decision log."""

    reason: str | None = Field(default=None, min_length=REASON_MIN, max_length=REASON_MAX)
