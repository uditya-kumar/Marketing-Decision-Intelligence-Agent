"""Scenario contract: validate params, perturb the modifiers, return a ground-truth entry."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, ClassVar

from pydantic import BaseModel, ConfigDict, ValidationError

from novawear_sim.errors import ScenarioError
from novawear_sim.scenarios.ground_truth import (
    AffectedMetric,
    EntityLevel,
    GroundTruthEvent,
    Onset,
)

if TYPE_CHECKING:
    from novawear_sim.config.schedule import ScheduledEvent, Target
    from novawear_sim.scenarios.context import ScenarioContext
    from novawear_sim.world.rng import FloatArray


class NoParams(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


def scaled(intensity: FloatArray, multiplier: float) -> FloatArray:
    """Per-day multiplier moving from 1 (intensity 0) to `multiplier` (intensity 1)."""
    return 1.0 + (multiplier - 1.0) * intensity


class Scenario[P: BaseModel](ABC):
    kind: ClassVar[str]
    onset: ClassVar[Onset]
    target_levels: ClassVar[tuple[EntityLevel, ...]]
    affected_metrics: ClassVar[tuple[tuple[str, str], ...]] = ()
    expected_signal_type: ClassVar[str | None] = None
    expected_action: ClassVar[str | None] = None
    params_model: type[P]

    def resolve_target(self, target: Target) -> Target:
        """Hook to fill scenario-specific target defaults (e.g. device)."""
        return target

    @abstractmethod
    def apply(self, event: ScheduledEvent, target: Target, params: P, ctx: ScenarioContext) -> None:
        """Multiply the relevant `ctx.mods` arrays in place over the event window."""

    def record(self, event: ScheduledEvent, ctx: ScenarioContext) -> GroundTruthEvent:
        try:
            params = self.params_model.model_validate(event.params)
        except ValidationError as exc:
            raise ScenarioError(f"event {event.id!r}: invalid params:\n{exc}") from exc
        target = self.resolve_target(event.target)
        ref = ctx.describe(target)
        if ref.level not in self.target_levels:
            raise ScenarioError(
                f"event {event.id!r}: {self.kind} targets {list(self.target_levels)}, "
                f"got {ref.level}"
            )
        if ref.level != "account" and not ctx.slot_mask(target).any():
            raise ScenarioError(f"event {event.id!r}: target matches no ad rows")
        self.apply(event, target, params, ctx)
        return GroundTruthEvent(
            id=event.id,
            type=self.kind,
            start=event.start,
            end=event.end,
            onset=self.onset,
            target=ref,
            affected_metrics=[
                AffectedMetric.model_validate({"metric": m, "direction": d})
                for m, d in self.affected_metrics
            ],
            expected_signal_type=self.expected_signal_type,
            expected_action=self.expected_action,
            params=params.model_dump(),
        )
