"""`channel_opportunity`: a channel (or campaign) becomes more efficient and has headroom.

Returns per rupee rise and the saturation point moves out, so ROAS beats target and extra
budget would still pay back — the case for a budget shift towards it.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

from novawear_sim.scenarios.base import Scenario, scaled
from novawear_sim.world.saturation import yield_preserving_vmax

if TYPE_CHECKING:
    from novawear_sim.config.schedule import ScheduledEvent, Target
    from novawear_sim.scenarios.context import ScenarioContext


class ChannelOpportunityParams(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    uplift: float = Field(default=1.35, gt=1)
    headroom: float = Field(default=1.6, ge=1)
    ramp_days: int = Field(default=3, ge=1)


class ChannelOpportunity(Scenario[ChannelOpportunityParams]):
    kind = "channel_opportunity"
    onset = "gradual"
    target_levels = ("channel", "campaign")
    affected_metrics = (("roas", "up"), ("cpa", "down"), ("cvr", "up"))
    expected_signal_type = "opportunity"
    expected_action = "budget_shift"
    params_model = ChannelOpportunityParams

    def apply(
        self,
        event: ScheduledEvent,
        target: Target,
        params: ChannelOpportunityParams,
        ctx: ScenarioContext,
    ) -> None:
        ramp = ctx.intensity(event, params.ramp_days)
        ref = ctx.describe(target)
        assert ref.channel is not None
        c = ctx.index("channel", ref.channel)
        k_mult = scaled(ramp, params.headroom)
        ctx.mods.k[:, c] *= k_mult
        ctx.mods.vmax[:, c] *= yield_preserving_vmax(ctx.world.channels[c].hill, k_mult)
        if ref.level == "channel":
            ctx.mods.vmax[:, c] *= scaled(ramp, params.uplift)
            return
        # Campaign-level: the uplift splits between clicking and buying, like channel efficiency.
        rows = ctx.slot_mask(target)
        half = scaled(ramp, math.sqrt(params.uplift))[:, None]
        ctx.mods.ctr[:, rows] *= half
        ctx.mods.atc[:, rows] *= half
