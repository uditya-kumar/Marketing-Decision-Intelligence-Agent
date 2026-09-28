"""`tracking_break`: a platform's pixel/CAPI stops reporting most purchases.

Only the platform's *reported* conversions and revenue fall; real orders, GA4 and the store
are unaffected. Acting on the platform numbers here would be a mistake.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

from novawear_sim.scenarios.base import Scenario, scaled

if TYPE_CHECKING:
    from novawear_sim.config.schedule import ScheduledEvent, Target
    from novawear_sim.scenarios.context import ScenarioContext


class TrackingBreakParams(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    capture: float = Field(default=0.15, ge=0, lt=1)


class TrackingBreak(Scenario[TrackingBreakParams]):
    kind = "tracking_break"
    onset = "abrupt"
    target_levels = ("source",)
    affected_metrics = (("platform_conversions", "down"), ("platform_roas", "down"))
    expected_signal_type = None  # a data-trust finding, not a performance signal
    expected_action = "fix_tracking"
    params_model = TrackingBreakParams

    def apply(
        self,
        event: ScheduledEvent,
        target: Target,
        params: TrackingBreakParams,
        ctx: ScenarioContext,
    ) -> None:
        rows = ctx.slot_mask(target)
        ctx.mods.attribution[:, rows] *= scaled(ctx.intensity(event)[:, None], params.capture)
