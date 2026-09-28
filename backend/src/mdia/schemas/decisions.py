"""API DTOs for the decision log (``/decisions``)."""

from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, ConfigDict

from mdia.models.experiments import DecisionKind
from mdia.schemas.experiments import ExperimentOut
from mdia.schemas.opportunities import OpportunityOut


class _Out(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class DecisionOut(_Out):
    """One entry of the timeline: the call, the opportunity behind it, and the outcome."""

    id: int
    kind: DecisionKind
    reason: str | None
    impact: float | None
    at: dt.datetime
    opportunity: OpportunityOut
    experiment: ExperimentOut | None


class DecisionListOut(_Out):
    decisions: list[DecisionOut]
