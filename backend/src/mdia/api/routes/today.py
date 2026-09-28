"""The Today screen's data: KPI summary and trend, data trust and budget pacing."""

from __future__ import annotations

from fastapi import APIRouter

from mdia.api.deps import TodayServiceDep  # noqa: TC001 - FastAPI resolves it at runtime
from mdia.schemas.today import TodayOut

router = APIRouter(prefix="/today", tags=["today"])


@router.get("", response_model=TodayOut)
def today(service: TodayServiceDep) -> TodayOut:
    """Headline KPIs for the week to the as-of date vs the week before, with goal markers,
    plus the trust status of every source and month-to-date budget pacing."""
    return TodayOut.model_validate(service.today())
