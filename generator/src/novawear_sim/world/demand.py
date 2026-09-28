"""Seeded daily demand index: growth trend × weekly seasonality × payday × festive × AR(1) noise."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from novawear_sim.config.models import WEEKDAYS, Demand

if TYPE_CHECKING:
    from novawear_sim.world.rng import FloatArray, RandomStreams
    from novawear_sim.world.timeline import Timeline


def weekly_profile(demand: Demand) -> FloatArray:
    """Weekday multipliers (Mon..Sun) normalised to mean 1 so they shape but don't scale demand."""
    raw = np.asarray([demand.weekly[d] for d in WEEKDAYS])
    return raw / raw.mean()


def demand_index(
    demand: Demand, timeline: Timeline, festive: FloatArray, streams: RandomStreams
) -> FloatArray:
    years = (timeline.ordinals - timeline.ordinals[0]) / 365.25
    trend = (1.0 + demand.annual_growth) ** years
    weekly = weekly_profile(demand)[timeline.weekdays]
    payday = np.asarray(
        [1.0 + demand.payday.uplift * (d.day in demand.payday.days) for d in timeline.dates]
    )
    shocks = streams.normal("demand", 1)[:, 0] * demand.noise.sigma
    noise = np.zeros(timeline.size)
    rho = demand.noise.persistence
    for i in range(timeline.size):
        prev = noise[i - 1] if i else 0.0
        noise[i] = rho * prev + np.sqrt(1 - rho**2) * shocks[i]
    return np.asarray(trend * weekly * payday * festive * np.exp(noise), dtype=np.float64)
