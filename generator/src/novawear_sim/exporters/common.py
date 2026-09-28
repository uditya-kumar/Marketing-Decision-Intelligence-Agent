"""Shared helpers to turn `(days, slots)` simulation arrays into long export rows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np
import numpy.typing as npt

from novawear_sim.errors import GeneratorError
from novawear_sim.world.ids import platform_id

if TYPE_CHECKING:
    from datetime import date

    from novawear_sim.engine import Simulation


@dataclass(frozen=True)
class AdRows:
    """Flattened ad rows for one source over a window (only rows that served impressions)."""

    days: npt.NDArray[np.int64]  # index into the timeline
    slots: npt.NDArray[np.int64]  # index into the slot grid

    def take(self, values: npt.NDArray[np.generic]) -> npt.NDArray[np.generic]:
        return values[self.days, self.slots]


def window_indices(sim: Simulation, start: date, end: date) -> npt.NDArray[np.int64]:
    if start < sim.timeline.dates[0] or end > sim.timeline.dates[-1] or end < start:
        raise GeneratorError(
            f"window {start}..{end} is outside the simulated range "
            f"{sim.timeline.dates[0]}..{sim.timeline.dates[-1]}"
        )
    return np.flatnonzero(sim.timeline.mask(start, end)).astype(np.int64)


def ad_rows(sim: Simulation, source: str, start: date, end: date) -> AdRows:
    days = window_indices(sim, start, end)
    is_source = np.asarray([ch.source == source for ch in sim.world.channels])
    slot_ids = np.flatnonzero(is_source[sim.world.slots.channel]).astype(np.int64)
    d, s = (g.ravel() for g in np.meshgrid(days, slot_ids, indexing="ij"))
    served = sim.delivery.impressions[d, s] > 0
    return AdRows(days=d[served], slots=s[served])


def entity_columns(sim: Simulation, rows: AdRows, source: str) -> dict[str, list[str]]:
    """Names and platform IDs of the campaign / ad set / ad behind each row."""
    world, slots = sim.world, sim.world.slots
    campaigns = [(c.name, platform_id(source, "campaign", c.key)) for c in world.campaigns]
    ad_sets = [(a.name, platform_id(source, "ad_set", a.key)) for a in world.ad_sets]
    creatives = [(c.name, platform_id(source, "creative", c.key)) for c in world.creatives]
    camp = [campaigns[i] for i in slots.campaign[rows.slots]]
    ad_set = [ad_sets[i] for i in slots.ad_set[rows.slots]]
    creative = [creatives[i] for i in slots.creative[rows.slots]]
    return {
        "campaign": [n for n, _ in camp],
        "campaign_id": [i for _, i in camp],
        "ad_set": [n for n, _ in ad_set],
        "ad_set_id": [i for _, i in ad_set],
        "ad": [n for n, _ in creative],
        "ad_id": [i for _, i in creative],
    }


def row_dates(sim: Simulation, rows: AdRows) -> list[date]:
    return [sim.timeline.dates[i] for i in rows.days]
