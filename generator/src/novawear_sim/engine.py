"""Run the NovaWear world from the epoch to an end date under a scenario schedule."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from novawear_sim.errors import GeneratorError
from novawear_sim.scenarios.context import ScenarioContext
from novawear_sim.scenarios.runner import apply_schedule
from novawear_sim.world.demand import demand_index
from novawear_sim.world.entities import World, build_world
from novawear_sim.world.festive import CalendarEffects, calendar_effects
from novawear_sim.world.media import Delivery, deliver
from novawear_sim.world.modifiers import Modifiers
from novawear_sim.world.paid import PaidOutcome, paid_outcome
from novawear_sim.world.rng import FloatArray, RandomStreams
from novawear_sim.world.store import StoreDaily, store_daily
from novawear_sim.world.timeline import Timeline
from novawear_sim.world.web import WebTraffic, organic_traffic, web_traffic

if TYPE_CHECKING:
    from datetime import date

    from novawear_sim.config.models import WorldConfig
    from novawear_sim.config.schedule import Schedule
    from novawear_sim.scenarios.ground_truth import GroundTruthEvent
    from novawear_sim.world.funnel import FunnelCounts


@dataclass(frozen=True)
class Simulation:
    world: World
    timeline: Timeline
    seed: int
    festive: CalendarEffects
    demand: FloatArray
    delivery: Delivery
    paid: PaidOutcome
    organic: FunnelCounts
    web: WebTraffic
    store: StoreDaily
    events: list[GroundTruthEvent]


def simulate(config: WorldConfig, schedule: Schedule, seed: int, end: date) -> Simulation:
    if end < config.timeline.epoch:
        raise GeneratorError(f"end date {end} is before the world epoch {config.timeline.epoch}")
    world = build_world(config)
    timeline = Timeline.between(config.timeline.epoch, end)
    streams = RandomStreams(seed, timeline.ordinals)

    mods = Modifiers.neutral(
        timeline.size, world.slots.size, len(world.creatives), len(world.channels)
    )
    events = apply_schedule(schedule, ScenarioContext(world, timeline, mods))

    festive = calendar_effects(config.calendar, timeline)
    demand = demand_index(config.demand, timeline, festive.demand, streams)
    delivery = deliver(world, timeline, mods, festive, demand, streams)
    paid = paid_outcome(world, delivery, mods, festive, demand, streams)
    organic_sources, organic_devices, organic = organic_traffic(
        world, timeline, festive, demand, streams
    )
    web = web_traffic(world, paid.funnel, organic, organic_sources, organic_devices, streams)
    store = store_daily(paid.funnel, organic, festive, config.funnel, streams)
    return Simulation(
        world=world,
        timeline=timeline,
        seed=seed,
        festive=festive,
        demand=demand,
        delivery=delivery,
        paid=paid,
        organic=organic,
        web=web,
        store=store,
        events=events,
    )
