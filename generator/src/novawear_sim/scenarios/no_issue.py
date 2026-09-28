"""`no_issue`: a quiet window — nothing injected. Used to measure false positives."""

from __future__ import annotations

from typing import TYPE_CHECKING

from novawear_sim.scenarios.base import NoParams, Scenario

if TYPE_CHECKING:
    from novawear_sim.config.schedule import ScheduledEvent, Target
    from novawear_sim.scenarios.context import ScenarioContext


class NoIssue(Scenario[NoParams]):
    kind = "no_issue"
    onset = "none"
    target_levels = ("account", "source", "channel")
    params_model = NoParams

    def apply(
        self, event: ScheduledEvent, target: Target, params: NoParams, ctx: ScenarioContext
    ) -> None:
        return None
