"""Typed models for `world.yaml` — the hidden truth of the NovaWear world."""

from __future__ import annotations

from datetime import date
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from novawear_sim.config.channels import Channel

Weekday = Literal["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
WEEKDAYS: tuple[Weekday, ...] = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
Device = Literal["mobile", "desktop"]
DEVICES: tuple[Device, ...] = ("mobile", "desktop")


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Brand(_Model):
    name: str
    currency: str
    timezone: str
    gross_margin: float = Field(gt=0, lt=1)


class Timeline(_Model):
    epoch: date
    default_end: date

    @model_validator(mode="after")
    def _end_after_epoch(self) -> Self:
        if self.default_end <= self.epoch:
            raise ValueError("timeline.default_end must be after timeline.epoch")
        return self


class Payday(_Model):
    days: list[int]
    uplift: float = Field(ge=0)


class DemandNoise(_Model):
    sigma: float = Field(ge=0)
    persistence: float = Field(ge=0, lt=1)


class Demand(_Model):
    annual_growth: float
    weekly: dict[Weekday, float]
    payday: Payday
    noise: DemandNoise

    @model_validator(mode="after")
    def _all_weekdays(self) -> Self:
        if set(self.weekly) != set(WEEKDAYS):
            raise ValueError("demand.weekly must define every weekday")
        return self


class CalendarEvent(_Model):
    name: str
    start: date
    end: date
    peak: date | None = None
    demand_uplift: float = Field(ge=0)
    cpm_uplift: float = Field(ge=0)
    aov_uplift: float = Field(gt=-1)
    discount_rate: float = Field(ge=0, lt=1)

    @model_validator(mode="after")
    def _ordered(self) -> Self:
        if self.end < self.start:
            raise ValueError(f"calendar event {self.name!r} ends before it starts")
        if self.peak is not None and not self.start <= self.peak <= self.end:
            raise ValueError(f"calendar event {self.name!r} peak is outside its window")
        return self


class AgeGroup(_Model):
    mix: float = Field(gt=0)
    ctr: float = Field(gt=0)
    cpm: float = Field(gt=0)
    intent: float = Field(gt=0)


class DeviceProfile(_Model):
    ctr: float = Field(gt=0)
    cpm: float = Field(gt=0)
    engage_rate: float = Field(gt=0, lt=1)


class Segments(_Model):
    age_groups: dict[str, AgeGroup]
    devices: dict[Device, DeviceProfile]


class DemandResponse(_Model):
    sessions: float = Field(ge=0)
    ctr: float = Field(ge=0)
    conversion: float = Field(ge=0)


class NewCustomerShare(_Model):
    paid: float = Field(ge=0, le=1)
    organic: float = Field(ge=0, le=1)


class Shipping(_Model):
    share_of_orders: float = Field(ge=0, le=1)
    fee: float = Field(ge=0)


class Funnel(_Model):
    landing_rate: float = Field(gt=0, le=1)
    atc_rate: float = Field(gt=0, lt=1)
    checkout_rate: float = Field(gt=0, lt=1)
    purchase_rate: float = Field(gt=0, lt=1)
    aov: float = Field(gt=0)
    aov_noise: float = Field(ge=0)
    ga_capture: float = Field(gt=0, le=1)
    new_customer_share: NewCustomerShare
    refund_rate: float = Field(ge=0, lt=1)
    refund_lag_days: int = Field(ge=0)
    tax_rate: float = Field(ge=0)
    shipping: Shipping


class Fatigue(_Model):
    memory: float = Field(ge=0, lt=1)
    threshold: float = Field(ge=0)
    sensitivity: float = Field(ge=0)


class OrganicSource(_Model):
    source_medium: str
    sessions: float = Field(gt=0)
    intent: float = Field(gt=0)
    mobile_share: float = Field(ge=0, le=1)
    send_days: list[Weekday] = Field(default_factory=list)
    send_multiplier: float = Field(default=1.0, ge=1)


class WorldConfig(_Model):
    brand: Brand
    timeline: Timeline
    demand: Demand
    calendar: list[CalendarEvent]
    segments: Segments
    demand_response: DemandResponse
    funnel: Funnel
    fatigue: Fatigue
    organic_sources: list[OrganicSource]
    channels: list[Channel] = Field(min_length=1)

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        keys: list[str] = []
        ages = set(self.segments.age_groups)
        for channel in self.channels:
            keys.append(channel.key)
            for campaign in channel.campaigns:
                keys.append(campaign.key)
                for ad_set in campaign.ad_sets:
                    keys.append(ad_set.key)
                    keys.extend(c.key for c in ad_set.creatives)
                    if ad_set.age_mix is not None and set(ad_set.age_mix) != ages:
                        raise ValueError(f"ad set {ad_set.key!r} age_mix must cover {sorted(ages)}")
        duplicates = sorted({k for k in keys if keys.count(k) > 1})
        if duplicates:
            raise ValueError(f"entity keys must be unique, duplicated: {duplicates}")
        if set(self.segments.devices) != set(DEVICES):
            raise ValueError(f"segments.devices must define {list(DEVICES)}")
        return self
