"""Small array helpers shared by the simulation steps."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from novawear_sim.world.rng import FloatArray, IntArray


def group_sum(values: FloatArray, groups: IntArray, n_groups: int) -> FloatArray:
    """Sum `(days, items)` columns into `(days, n_groups)` by each item's group index."""
    onehot = np.zeros((groups.size, n_groups))
    onehot[np.arange(groups.size), groups] = 1.0
    return np.asarray(values @ onehot, dtype=np.float64)


def normalise_within(weights: FloatArray, groups: IntArray, n_groups: int) -> FloatArray:
    """Rescale `(days, items)` weights so each group sums to 1 per day (0 for empty groups)."""
    totals = group_sum(weights, groups, n_groups)[:, groups]
    return np.divide(weights, totals, out=np.zeros_like(weights), where=totals > 0)
