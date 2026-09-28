"""Typed models for `scenarios.yaml` — named schedules of injected scenarios."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from novawear_sim.config.models import Device


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Target(_Model):
    """Which slice of the world a scenario hits; each scenario says which fields it needs."""

    source: str | None = None
    channel: str | None = None
    campaign: str | None = None
    ad_set: str | None = None
    creative: str | None = None
    device: Device | None = None
    age_group: str | None = None


class ScheduledEvent(_Model):
    id: str
    type: str
    start: date
    days: int = Field(ge=1)
    target: Target = Target()
    params: dict[str, Any] = Field(default_factory=dict)

    @property
    def end(self) -> date:
        """Last affected day (inclusive)."""
        return self.start + timedelta(days=self.days - 1)


class Schedule(_Model):
    description: str = ""
    events: list[ScheduledEvent] = Field(default_factory=list)


class ScheduleFile(_Model):
    schedules: dict[str, Schedule]
