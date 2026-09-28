"""`cpc_spike`: auction competition drives CPM (hence CPC and CPA) up; CTR and CVR hold."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

from novawear_sim.scenarios.base import Scenario, scaled

if TYPE_CHECKING:
    from novawear_sim.config.schedule import ScheduledEvent, Target
    from novawear_sim.scenarios.context import ScenarioContext


class CpcSpikeParams(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    cpm_multiplier: float = Field(default=1.6, gt=1)
    ramp_days: int = Field(default=2, ge=1)


class CpcSpike(Scenario[CpcSpikeParams]):
    kind = "cpc_spike"
    onset = "abrupt"
    target_levels = ("channel", "campaign")
    affected_metrics = (("cpm", "up"), ("cpc", "up"), ("cpa", "up"), ("impressions", "down"))
    expected_signal_type = "performance"
    expected_action = "budget_shift"
    params_model = CpcSpikeParams

    def apply(
        self, event: ScheduledEvent, target: Target, params: CpcSpikeParams, ctx: ScenarioContext
    ) -> None:
        rows = ctx.slot_mask(target)
        ramp = ctx.intensity(event, params.ramp_days)[:, None]
        ctx.mods.cpm[:, rows] *= scaled(ramp, params.cpm_multiplier)
