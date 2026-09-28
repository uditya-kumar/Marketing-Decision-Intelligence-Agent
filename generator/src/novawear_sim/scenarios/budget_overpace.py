"""`budget_overpace`: a channel spends well above its monthly plan's daily pace."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

from novawear_sim.scenarios.base import Scenario, scaled

if TYPE_CHECKING:
    from novawear_sim.config.schedule import ScheduledEvent, Target
    from novawear_sim.scenarios.context import ScenarioContext


class BudgetOverpaceParams(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    factor: float = Field(default=1.38, gt=1)


class BudgetOverpace(Scenario[BudgetOverpaceParams]):
    kind = "budget_overpace"
    onset = "abrupt"
    target_levels = ("channel",)
    affected_metrics = (("spend", "up"),)
    expected_signal_type = "pacing"
    expected_action = "adjust_pacing"
    params_model = BudgetOverpaceParams

    def apply(
        self,
        event: ScheduledEvent,
        target: Target,
        params: BudgetOverpaceParams,
        ctx: ScenarioContext,
    ) -> None:
        rows = ctx.slot_mask(target)
        ctx.mods.spend[:, rows] *= scaled(ctx.intensity(event)[:, None], params.factor)
