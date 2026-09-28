"""API DTOs for business settings (FR-1). Invalid values are rejected here with a 422."""

from __future__ import annotations

import datetime as dt
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from mdia.domain.sources import Channel

Rupees = Annotated[float, Field(ge=0)]


class FestiveWindow(BaseModel):
    """A sale or festival where big swings are expected, so signals are suppressed."""

    model_config = ConfigDict(from_attributes=True)

    name: str = Field(min_length=1, max_length=64)
    start: dt.date
    end: dt.date

    @model_validator(mode="after")
    def _ends_after_start(self) -> Self:
        if self.end < self.start:
            raise ValueError("a festive window must end on or after its start")
        return self


class SettingsIn(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    business_name: str = Field(min_length=1, max_length=128)
    gross_margin_pct: float = Field(gt=0, le=100)
    target_cpa: float | None = Field(default=None, gt=0)
    target_roas: float | None = Field(default=None, gt=0)
    monthly_revenue_goal: float | None = Field(default=None, gt=0)
    monthly_budgets: dict[Channel, Rupees] = Field(default_factory=dict)
    festive_windows: list[FestiveWindow] = Field(default_factory=list)
    protected_campaign_ids: list[int] = Field(default_factory=list)


class SettingsOut(BaseModel):
    """``settings`` is null until the first save, which is what the first-run flow keys on."""

    model_config = ConfigDict(from_attributes=True)

    configured: bool
    settings: SettingsIn | None
    break_even_roas: float | None
    target_roas_profitable: bool | None


class CampaignOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    channel_id: Channel
    name: str
