"""The Today screen's data (FR-4.3 v1: KPI summary and trend)."""

from __future__ import annotations

from fastapi import APIRouter

from mdia.api.deps import MetricsServiceDep  # noqa: TC001 - FastAPI resolves it at runtime
from mdia.schemas.metrics import TodayOut

router = APIRouter(prefix="/today", tags=["today"])


@router.get("", response_model=TodayOut)
def today(service: MetricsServiceDep) -> TodayOut:
    """Headline KPIs for the week to the as-of date vs the week before, with goal markers."""
    return TodayOut.model_validate(service.today())
