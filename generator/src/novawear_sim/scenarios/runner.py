"""Apply a schedule to the world's modifiers and collect its ground truth."""

from __future__ import annotations

from typing import TYPE_CHECKING

from novawear_sim.errors import ScenarioError
from novawear_sim.scenarios.registry import get_scenario

if TYPE_CHECKING:
    from novawear_sim.config.schedule import Schedule
    from novawear_sim.scenarios.context import ScenarioContext
    from novawear_sim.scenarios.ground_truth import GroundTruthEvent

QUIET = "no_issue"


def apply_schedule(schedule: Schedule, ctx: ScenarioContext) -> list[GroundTruthEvent]:
    ids = [e.id for e in schedule.events]
    duplicates = sorted({i for i in ids if ids.count(i) > 1})
    if duplicates:
        raise ScenarioError(f"event ids must be unique, duplicated: {duplicates}")
    entries = [get_scenario(e.type).record(e, ctx) for e in schedule.events]
    _check_quiet_windows(entries, ctx)
    return entries


def _check_quiet_windows(entries: list[GroundTruthEvent], ctx: ScenarioContext) -> None:
    """A `no_issue` window is only a valid false-positive test if nothing else touches it."""
    for quiet in (e for e in entries if e.type == QUIET):
        scope = ctx.channels_of(quiet.target)
        for other in entries:
            if other.type == QUIET or not other.overlaps(quiet.start, quiet.end):
                continue
            if scope & ctx.channels_of(other.target):
                raise ScenarioError(
                    f"quiet window {quiet.id!r} overlaps {other.type} event {other.id!r}"
                )
