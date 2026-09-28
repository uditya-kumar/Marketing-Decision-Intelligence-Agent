"""API DTOs for data trust (``/trust``) and budget pacing, both also embedded in ``/today``."""

from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, ConfigDict, computed_field

from mdia.domain.pacing import PacingStatus
from mdia.domain.sources import SOURCE_LABELS, Channel, Source
from mdia.domain.trust import TrustStatus
from mdia.schemas.metrics import PeriodOut


class _Out(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class FreshnessOut(_Out):
    last_date: dt.date | None
    days_behind: int
    missing_dates: list[dt.date]


class TrackingOut(_Out):
    status: TrustStatus
    ratio_change: float
    since: dt.date | None
    conversions_change_pct: float | None
    orders_change_pct: float | None


class SourceTrustOut(_Out):
    source: Source
    status: TrustStatus
    freshness: FreshnessOut
    tracking: TrackingOut | None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def label(self) -> str:
        return SOURCE_LABELS[self.source]


class TrustOut(_Out):
    as_of_date: dt.date | None
    sources: list[SourceTrustOut]


class PacingOut(_Out):
    budget: float
    spent: float
    spent_pct: float
    remaining_budget: float
    month_elapsed_pct: float
    projected: float
    status: PacingStatus
    daily_run_rate: float
    suggested_daily: float | None


class ChannelPacingOut(_Out):
    channel: Channel
    pacing: PacingOut

    @computed_field  # type: ignore[prop-decorator]
    @property
    def label(self) -> str:
        return SOURCE_LABELS[self.channel]


class PacingViewOut(_Out):
    month: PeriodOut | None
    total: PacingOut | None
    channels: list[ChannelPacingOut]
