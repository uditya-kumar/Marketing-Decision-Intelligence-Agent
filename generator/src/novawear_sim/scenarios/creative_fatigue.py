"""`creative_fatigue`: a creative's audience saturates, so frequency climbs and CTR decays.

The CTR drop is not injected directly — it emerges from the world's frequency-driven fatigue
model. When the window ends the creative is refreshed and the exposure stock slowly decays.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

from novawear_sim.errors import ScenarioError
from novawear_sim.scenarios.base import Scenario, scaled

if TYPE_CHECKING:
    from novawear_sim.config.schedule import ScheduledEvent, Target
    from novawear_sim.scenarios.context import ScenarioContext


class CreativeFatigueParams(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    audience_floor: float = Field(default=0.25, gt=0, lt=1)
    ramp_days: int = Field(default=5, ge=1)


class CreativeFatigue(Scenario[CreativeFatigueParams]):
    kind = "creative_fatigue"
    onset = "gradual"
    target_levels = ("creative",)
    affected_metrics = (("frequency", "up"), ("ctr", "down"), ("cpc", "up"), ("cpa", "up"))
    expected_signal_type = "creative"
    expected_action = "rotate_creative"
    params_model = CreativeFatigueParams

    def apply(
        self,
        event: ScheduledEvent,
        target: Target,
        params: CreativeFatigueParams,
        ctx: ScenarioContext,
    ) -> None:
        assert target.creative is not None
        k = ctx.index("creative", target.creative)
        channel = ctx.world.channels[int(ctx.world.creative_channel[k])]
        if channel.fatigue_sensitivity == 0:
            raise ScenarioError(f"event {event.id!r}: {channel.key} creatives do not fatigue")
        ramp = ctx.intensity(event, params.ramp_days)
        ctx.mods.audience[:, k] *= scaled(ramp, params.audience_floor)
