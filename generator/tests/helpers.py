"""Array helpers for asserting on simulation slices."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from datetime import date

    from novawear_sim.engine import Simulation


def slots_where(sim: Simulation, **keys: str) -> np.ndarray:
    """Boolean slot mask, e.g. `slots_where(sim, channel="meta_ads", device="mobile")`."""
    world, slots = sim.world, sim.world.slots
    mask = np.ones(slots.size, dtype=bool)
    for level, key in keys.items():
        if level == "device":
            mask &= np.asarray(world.devices)[slots.device] == key
        elif level == "age_group":
            mask &= np.asarray(world.ages)[slots.age] == key
        else:
            mask &= getattr(slots, level) == world.index_of(level, key)  # type: ignore[arg-type]
    return mask


def total(values: np.ndarray, sim: Simulation, start: date, end: date, slots: np.ndarray) -> float:
    """Sum of a `(days, slots)` array over a date window and slot mask."""
    days = sim.timeline.mask(start, end)
    return float(values[np.ix_(days, slots)].sum())
