"""Multiplicative knobs that scenarios turn; all start at 1 (the undisturbed world)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from novawear_sim.world.rng import FloatArray


@dataclass(frozen=True)
class Modifiers:
    # (days, slots)
    spend: FloatArray
    cpm: FloatArray
    ctr: FloatArray
    mix: FloatArray  # weight of a slot in its ad set's delivery before renormalising
    engage: FloatArray
    atc: FloatArray
    attribution: FloatArray  # platform-reported conversions per true purchase
    # (days, creatives)
    audience: FloatArray
    # (days, channels)
    vmax: FloatArray
    k: FloatArray

    @classmethod
    def neutral(cls, days: int, slots: int, creatives: int, channels: int) -> Modifiers:
        def ones(width: int) -> FloatArray:
            return np.ones((days, width))

        return cls(
            spend=ones(slots),
            cpm=ones(slots),
            ctr=ones(slots),
            mix=ones(slots),
            engage=ones(slots),
            atc=ones(slots),
            attribution=ones(slots),
            audience=ones(creatives),
            vmax=ones(channels),
            k=ones(channels),
        )
