"""`audience_mismatch`: an ad set's delivery drifts into a low-intent age group.

Clicks keep coming but that segment rarely buys, so the ad set's CVR falls and CPA rises —
visible as a cross-segment divergence.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

from novawear_sim.scenarios.base import Scenario, scaled

if TYPE_CHECKING:
    from novawear_sim.config.schedule import ScheduledEvent, Target
    from novawear_sim.scenarios.context import ScenarioContext

DEFAULT_AGE_GROUP = "18-24"


class AudienceMismatchParams(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    share_multiplier: float = Field(default=4.0, gt=1)
    intent_multiplier: float = Field(default=0.3, gt=0, lt=1)
    ramp_days: int = Field(default=2, ge=1)


class AudienceMismatch(Scenario[AudienceMismatchParams]):
    kind = "audience_mismatch"
    onset = "abrupt"
    target_levels = ("ad_set",)
    affected_metrics = (("cvr", "down"), ("cpa", "up"), ("roas", "down"))
    expected_signal_type = "audience"
    expected_action = "retarget_audience"
    params_model = AudienceMismatchParams

    def resolve_target(self, target: Target) -> Target:
        return target.model_copy(update={"age_group": target.age_group or DEFAULT_AGE_GROUP})

    def apply(
        self,
        event: ScheduledEvent,
        target: Target,
        params: AudienceMismatchParams,
        ctx: ScenarioContext,
    ) -> None:
        rows = ctx.slot_mask(target)
        ramp = ctx.intensity(event, params.ramp_days)[:, None]
        ctx.mods.mix[:, rows] *= scaled(ramp, params.share_multiplier)
        ctx.mods.atc[:, rows] *= scaled(ramp, params.intent_multiplier)
