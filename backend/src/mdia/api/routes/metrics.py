"""KPI series for charts and tables (FR-4.3)."""

from __future__ import annotations

import datetime as dt  # noqa: TC003 - FastAPI resolves the annotations at runtime
from typing import Annotated

from fastapi import APIRouter, Query

from mdia.api.deps import MetricsServiceDep  # noqa: TC001
from mdia.domain.kpi import Dimension, Metric  # noqa: TC001
from mdia.schemas.metrics import MetricsOut

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("", response_model=MetricsOut)
def metrics(
    service: MetricsServiceDep,
    metric: Metric,
    dimension: Dimension | None = None,
    days: Annotated[int, Query(ge=1, le=180)] = 30,
    end: dt.date | None = None,
) -> MetricsOut:
    """``metric`` per day, per ``dimension`` value, compared with the period before.

    ``end`` defaults to the as-of date.
    """
    return MetricsOut.model_validate(service.series(metric, dimension, days, end))
