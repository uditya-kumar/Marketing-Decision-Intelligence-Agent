"""Opportunities: the ranked list, one in full, and setting one aside (FR-6, FR-8, FR-9)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query

from mdia.api.deps import OpportunityServiceDep  # noqa: TC001 - FastAPI resolves it at runtime
from mdia.domain.opportunities import OpportunityKind
from mdia.models.analysis import OpportunityStatus
from mdia.schemas.opportunities import (
    DismissIn,
    OpportunityDetailOut,
    OpportunityListOut,
    OpportunityOut,
)

router = APIRouter(prefix="/opportunities", tags=["opportunities"])

StatusFilter = Annotated[list[OpportunityStatus] | None, Query()]
KindFilter = Annotated[OpportunityKind | None, Query()]


@router.get("", response_model=OpportunityListOut)
def list_opportunities(
    service: OpportunityServiceDep,
    status: StatusFilter = None,
    kind: KindFilter = None,
) -> OpportunityListOut:
    """Opportunities the last analysis found, most urgent first, filtered by status and kind."""
    found = service.find(status=status, kind=kind)
    return OpportunityListOut.model_validate({"opportunities": found})


@router.get("/{opportunity_id}", response_model=OpportunityDetailOut)
def get_opportunity(opportunity_id: int, service: OpportunityServiceDep) -> OpportunityDetailOut:
    """One opportunity in four sections: what happened, the evidence, the likely cause
    and the recommended action, with the signals behind them."""
    return OpportunityDetailOut.model_validate(service.get(opportunity_id))


@router.post("/{opportunity_id}/dismiss", response_model=OpportunityOut)
def dismiss_opportunity(
    opportunity_id: int, body: DismissIn, service: OpportunityServiceDep
) -> OpportunityOut:
    """Set an opportunity aside with a reason, so a re-run does not raise it again."""
    return OpportunityOut.model_validate(service.dismiss(opportunity_id, body.reason))
