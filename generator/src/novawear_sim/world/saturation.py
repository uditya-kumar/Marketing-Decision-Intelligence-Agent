"""Diminishing returns: per-channel Hill response to daily spend."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import numpy.typing as npt

if TYPE_CHECKING:
    from novawear_sim.config.channels import Hill
    from novawear_sim.world.rng import FloatArray


def hill_response(
    spend: npt.ArrayLike, hill: Hill, vmax_mult: npt.ArrayLike = 1.0, k_mult: npt.ArrayLike = 1.0
) -> FloatArray:
    s = np.maximum(np.asarray(spend, dtype=np.float64), 0.0)
    k = hill.k * np.asarray(k_mult, dtype=np.float64)
    vmax = hill.vmax * np.asarray(vmax_mult, dtype=np.float64)
    return np.asarray(vmax * s**hill.slope / (k**hill.slope + s**hill.slope), dtype=np.float64)


def efficiency(
    spend: npt.ArrayLike, hill: Hill, vmax_mult: npt.ArrayLike = 1.0, k_mult: npt.ArrayLike = 1.0
) -> FloatArray:
    """Response per rupee relative to the channel's reference spend (1.0 at reference, no uplift).

    Conversions scale with `spend × efficiency`, i.e. with the Hill response itself, so the
    per-rupee yield falls as spend grows past the reference.
    """
    s = np.maximum(np.asarray(spend, dtype=np.float64), 1.0)
    ref = hill.reference_spend
    ref_yield = hill_response(ref, hill) / ref
    return np.asarray(hill_response(s, hill, vmax_mult, k_mult) / s / ref_yield, dtype=np.float64)


def yield_preserving_vmax(hill: Hill, k_mult: npt.ArrayLike) -> FloatArray:
    """`vmax` multiplier that keeps the response at reference spend unchanged when `k` moves.

    Raising `k` alone would lower today's yield; pairing it with this multiplier moves only
    the saturation point, so extra budget pays back better without changing current returns.
    """
    ref = hill.reference_spend
    return np.asarray(hill_response(ref, hill) / hill_response(ref, hill, 1.0, k_mult))
