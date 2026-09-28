"""Site funnel: visitors → sessions → engaged → add to cart → checkout → purchase → order value."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np
import numpy.typing as npt

from novawear_sim.world.rng import FloatArray, IntArray, RandomStreams, binomial

if TYPE_CHECKING:
    from novawear_sim.config.models import Funnel

_MAX_RATE = 0.95


@dataclass(frozen=True)
class FunnelCounts:
    sessions: IntArray
    engaged: IntArray
    add_to_cart: IntArray
    checkout: IntArray
    purchases: IntArray
    revenue: FloatArray  # order value after discounts, before tax/shipping

    def __add__(self, other: FunnelCounts) -> FunnelCounts:
        return FunnelCounts(
            sessions=self.sessions + other.sessions,
            engaged=self.engaged + other.engaged,
            add_to_cart=self.add_to_cart + other.add_to_cart,
            checkout=self.checkout + other.checkout,
            purchases=self.purchases + other.purchases,
            revenue=self.revenue + other.revenue,
        )


def run_funnel(
    visitors: npt.NDArray[np.int64],
    landing_rate: float,
    engage_rate: npt.ArrayLike,
    atc_rate: npt.ArrayLike,
    aov: FloatArray,
    funnel: Funnel,
    streams: RandomStreams,
    stream_prefix: str,
) -> FunnelCounts:
    """Draw each step as a binomial of the previous; `aov` broadcasts to the visitor shape."""
    width = visitors.shape[1]

    def step(n: IntArray, p: npt.ArrayLike, name: str) -> IntArray:
        u = streams.uniform(f"{stream_prefix}:{name}", width)
        return binomial(n, np.minimum(np.asarray(p, dtype=np.float64), _MAX_RATE), u)

    sessions = step(visitors, landing_rate, "sessions")
    engaged = step(sessions, engage_rate, "engaged")
    atc = step(engaged, atc_rate, "atc")
    checkout = step(atc, funnel.checkout_rate, "checkout")
    purchases = step(checkout, funnel.purchase_rate, "purchase")

    # Sum of `n` order values: mean n·AOV, sd shrinking with sqrt(n).
    z = streams.normal(f"{stream_prefix}:order_value", width)
    spread = funnel.aov_noise * np.sqrt(np.maximum(purchases, 1))
    revenue = np.maximum(purchases * aov + z * spread * aov, 0.0) * (purchases > 0)
    return FunnelCounts(sessions, engaged, atc, checkout, purchases, np.round(revenue, 2))
