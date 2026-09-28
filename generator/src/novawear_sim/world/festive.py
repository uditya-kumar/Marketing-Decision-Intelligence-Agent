"""Festive / sale calendar: expected-change multipliers per day."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from novawear_sim.config.models import CalendarEvent
    from novawear_sim.world.rng import FloatArray
    from novawear_sim.world.timeline import Timeline

# Share of the peak effect felt on the first/last day of a peaked event.
_EDGE_INTENSITY = 0.35
_DEFAULT_DISCOUNT = 0.08


@dataclass(frozen=True)
class CalendarEffects:
    demand: FloatArray  # multiplier on purchase intent and organic traffic
    cpm: FloatArray  # auction pressure (before per-channel sensitivity)
    aov: FloatArray
    discount_rate: FloatArray


def event_intensity(event: CalendarEvent, timeline: Timeline) -> FloatArray:
    """0 outside the event; 1 at the peak, tapering linearly to the edges (flat if no peak)."""
    out = np.zeros(timeline.size)
    for i, day in enumerate(timeline.dates):
        if not event.start <= day <= event.end:
            continue
        if event.peak is None:
            out[i] = 1.0
            continue
        span = (
            (event.peak - event.start).days if day <= event.peak else (event.end - event.peak).days
        )
        distance = abs((day - event.peak).days)
        out[i] = 1.0 if span == 0 else 1.0 - (1.0 - _EDGE_INTENSITY) * distance / span
    return out


def calendar_effects(events: list[CalendarEvent], timeline: Timeline) -> CalendarEffects:
    demand = np.ones(timeline.size)
    cpm = np.ones(timeline.size)
    aov = np.ones(timeline.size)
    discount = np.full(timeline.size, _DEFAULT_DISCOUNT)
    for event in events:
        w = event_intensity(event, timeline)
        demand *= 1.0 + event.demand_uplift * w
        cpm *= 1.0 + event.cpm_uplift * w
        aov *= 1.0 + event.aov_uplift * w
        discount = np.where(w > 0, np.maximum(discount, event.discount_rate * w), discount)
    return CalendarEffects(demand=demand, cpm=cpm, aov=aov, discount_rate=discount)
