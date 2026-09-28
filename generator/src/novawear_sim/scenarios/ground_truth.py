"""Ground-truth records: what was injected, where and when. Only `evaluation/` reads these."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from pathlib import Path

EntityLevel = Literal["account", "source", "channel", "campaign", "ad_set", "creative"]
Onset = Literal["abrupt", "gradual", "none"]
Direction = Literal["up", "down"]


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class EntityRef(_Model):
    """The targeted slice, with names/IDs exactly as they appear in the exported CSVs."""

    level: EntityLevel
    key: str | None = None
    source: str | None = None
    channel: str | None = None
    campaign: str | None = None
    ad_set: str | None = None
    creative: str | None = None
    platform_id: str | None = None
    device: str | None = None
    age_group: str | None = None


class AffectedMetric(_Model):
    metric: str
    direction: Direction


class GroundTruthEvent(_Model):
    id: str
    type: str
    start: date
    end: date
    onset: Onset
    target: EntityRef
    affected_metrics: list[AffectedMetric]
    expected_signal_type: str | None
    expected_action: str | None
    params: dict[str, Any] = Field(default_factory=dict)

    def overlaps(self, start: date, end: date) -> bool:
        return self.start <= end and start <= self.end


class GroundTruth(_Model):
    generator: str = "novawear-sim"
    version: str
    seed: int
    schedule: str
    window_start: date
    window_end: date
    events: list[GroundTruthEvent]

    @classmethod
    def for_window(
        cls,
        events: list[GroundTruthEvent],
        *,
        version: str,
        seed: int,
        schedule: str,
        start: date,
        end: date,
    ) -> GroundTruth:
        return cls(
            version=version,
            seed=seed,
            schedule=schedule,
            window_start=start,
            window_end=end,
            events=[e for e in events if e.overlaps(start, end)],
        )

    def write(self, path: Path) -> None:
        path.write_text(self.model_dump_json(indent=2) + "\n", encoding="utf-8")
