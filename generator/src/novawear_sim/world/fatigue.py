"""Frequency-driven creative fatigue and reach.

Each creative carries an exposure stock — impressions per reachable person, decaying daily as
people forget. Once the stock passes a threshold, CTR decays exponentially. Shrinking the
reachable audience (or pushing more impressions into it) raises frequency and so drives fatigue.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from novawear_sim.config.models import Fatigue
    from novawear_sim.world.rng import FloatArray


def exposure_stock(impressions: FloatArray, audience: FloatArray, memory: float) -> FloatArray:
    """Stock `E[t] = memory·E[t-1] + I[t]/N[t]` per column (creative), shape `(days, creatives)`."""
    daily = impressions / np.maximum(audience, 1.0)
    stock = np.zeros_like(daily)
    for t in range(daily.shape[0]):
        stock[t] = (memory * stock[t - 1] if t else 0.0) + daily[t]
    return stock


def fatigue_multiplier(stock: FloatArray, config: Fatigue, sensitivity: FloatArray) -> FloatArray:
    """CTR multiplier in (0, 1]; `sensitivity` broadcasts per creative (0 disables fatigue)."""
    excess = np.maximum(stock - config.threshold, 0.0)
    return np.asarray(np.exp(-sensitivity * excess), dtype=np.float64)


def reach(impressions: FloatArray, audience: FloatArray) -> FloatArray:
    """Unique people reached when impressions land at random on an audience of size N."""
    n = np.maximum(audience, 1.0)
    return np.asarray(n * (1.0 - np.exp(-impressions / n)), dtype=np.float64)
