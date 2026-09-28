"""Typed models for the paid-media tree in `world.yaml`: channel → campaign → ad set → creative."""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Source = Literal["google_ads", "meta_ads"]


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Hill(_Model):
    """Channel response `vmax * S^slope / (k^slope + S^slope)` (daily spend S, in INR)."""

    vmax: float = Field(gt=0)
    k: float = Field(gt=0)
    slope: float = Field(gt=0)
    reference_spend: float = Field(gt=0)


class Creative(_Model):
    key: str
    name: str
    weight: float = Field(gt=0)
    ctr_factor: float = Field(default=1.0, gt=0)
    active_from: date | None = None
    active_to: date | None = None


class AdSet(_Model):
    key: str
    name: str
    region: str
    cpm: float = Field(gt=0)
    ctr: float = Field(gt=0, lt=1)
    intent: float = Field(gt=0)
    budget_share: float | None = Field(default=None, gt=0)
    audience_size: float = Field(default=1_000_000, gt=0)
    age_mix: dict[str, float] | None = None
    creatives: list[Creative] = Field(min_length=1)


class Campaign(_Model):
    key: str
    name: str
    budget_share: float = Field(gt=0)
    ad_sets: list[AdSet] = Field(min_length=1)


class MonthlyBudget(_Model):
    """Planned monthly spend; keys other than `default` are `YYYY-MM` overrides."""

    model_config = ConfigDict(extra="allow", frozen=True)
    default: float = Field(gt=0)

    def for_month(self, year: int, month: int) -> float:
        extra = self.model_extra or {}
        return float(extra.get(f"{year:04d}-{month:02d}", self.default))


class Channel(_Model):
    key: str
    name: str
    source: Source
    placement: str | None = None
    web_source: str
    attribution_ratio: float = Field(gt=0)
    mobile_share: float = Field(ge=0, le=1)
    fatigue_sensitivity: float | None = Field(default=None, ge=0)
    festive_cpm_sensitivity: float = Field(default=1.0, ge=0)
    hill: Hill
    monthly_budget: MonthlyBudget
    campaigns: list[Campaign] = Field(min_length=1)
