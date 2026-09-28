"""Analysis routes: the state of the detection run that follows every upload (FR-6)."""

from __future__ import annotations

from fastapi import APIRouter

from mdia.api.deps import AnalysisServiceDep  # noqa: TC001 - FastAPI resolves it at runtime
from mdia.schemas.analysis import AnalysisStatusOut

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.get("/status", response_model=AnalysisStatusOut)
def status(service: AnalysisServiceDep) -> AnalysisStatusOut:
    """Whether a run is in progress, and what the last one found."""
    return AnalysisStatusOut.model_validate(service.status())
