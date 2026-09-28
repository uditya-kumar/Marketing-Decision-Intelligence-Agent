"""`landing_page_break`: a campaign's landing page breaks on one device; visitors bounce.

Clicks and sessions are unchanged; engagement collapses, so CVR drops abruptly — a funnel
divergence rather than a media problem.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

from novawear_sim.scenarios.base import Scenario, scaled

if TYPE_CHECKING:
    from novawear_sim.config.schedule import ScheduledEvent, Target
    from novawear_sim.scenarios.context import ScenarioContext


class LandingPageBreakParams(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    engage_multiplier: float = Field(default=0.35, gt=0, lt=1)


class LandingPageBreak(Scenario[LandingPageBreakParams]):
    kind = "landing_page_break"
    onset = "abrupt"
    target_levels = ("channel", "campaign")
    affected_metrics = (("bounce_rate", "up"), ("cvr", "down"), ("cpa", "up"))
    expected_signal_type = "funnel"
    expected_action = "investigate_landing_page"
    params_model = LandingPageBreakParams

    def resolve_target(self, target: Target) -> Target:
        return target.model_copy(update={"device": target.device or "mobile"})

    def apply(
        self,
        event: ScheduledEvent,
        target: Target,
        params: LandingPageBreakParams,
        ctx: ScenarioContext,
    ) -> None:
        rows = ctx.slot_mask(target)
        ctx.mods.engage[:, rows] *= scaled(ctx.intensity(event)[:, None], params.engage_multiplier)
