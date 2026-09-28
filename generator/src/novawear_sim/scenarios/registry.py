"""All known scenario types by `type` name."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from novawear_sim.errors import ScenarioError
from novawear_sim.scenarios.audience_mismatch import AudienceMismatch
from novawear_sim.scenarios.budget_overpace import BudgetOverpace
from novawear_sim.scenarios.channel_opportunity import ChannelOpportunity
from novawear_sim.scenarios.cpc_spike import CpcSpike
from novawear_sim.scenarios.creative_fatigue import CreativeFatigue
from novawear_sim.scenarios.landing_page_break import LandingPageBreak
from novawear_sim.scenarios.no_issue import NoIssue
from novawear_sim.scenarios.tracking_break import TrackingBreak

if TYPE_CHECKING:
    from novawear_sim.scenarios.base import Scenario

SCENARIOS: dict[str, Scenario[Any]] = {
    s.kind: s
    for s in (
        NoIssue(),
        CreativeFatigue(),
        AudienceMismatch(),
        LandingPageBreak(),
        CpcSpike(),
        ChannelOpportunity(),
        TrackingBreak(),
        BudgetOverpace(),
    )
}


def get_scenario(kind: str) -> Scenario[Any]:
    if kind not in SCENARIOS:
        raise ScenarioError(f"unknown scenario type {kind!r}; known: {sorted(SCENARIOS)}")
    return SCENARIOS[kind]
