"""The decision log: what was decided, why, and how it turned out (FR-10.4)."""

from __future__ import annotations

from fastapi import APIRouter

from mdia.api.deps import DecisionServiceDep  # noqa: TC001 - FastAPI resolves it at runtime
from mdia.schemas.decisions import DecisionListOut

router = APIRouter(prefix="/decisions", tags=["decisions"])


@router.get("", response_model=DecisionListOut)
def list_decisions(service: DecisionServiceDep) -> DecisionListOut:
    """Every approval, rejection and dismissal, newest first, with its chain."""
    return DecisionListOut.model_validate({"decisions": service.find()})
