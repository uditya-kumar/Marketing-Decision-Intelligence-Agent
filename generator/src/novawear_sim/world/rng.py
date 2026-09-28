"""Seeded random streams keyed by (seed, stream, day).

Draws for a given day depend only on the seed, the stream name and the date — never on how
many days were simulated before it or on which scenarios are active. That keeps a `batch`
identical to the matching slice of a longer `backfill`, and lets a scenario run be compared
with its no-scenario counterfactual on the same noise (common random numbers).
"""

from __future__ import annotations

import zlib

import numpy as np
import numpy.typing as npt
from scipy import stats

FloatArray = npt.NDArray[np.float64]
IntArray = npt.NDArray[np.int64]

_EPS = 1e-12


class RandomStreams:
    def __init__(self, seed: int, day_ordinals: IntArray) -> None:
        self._seed = seed
        self._ordinals = day_ordinals

    def uniform(self, stream: str, width: int) -> FloatArray:
        """Uniforms in (0, 1), shape `(days, width)`."""
        stream_id = zlib.crc32(stream.encode())
        rows = [
            np.random.default_rng([self._seed, stream_id, int(day)]).random(width)
            for day in self._ordinals
        ]
        out = np.vstack(rows) if rows else np.empty((0, width))
        return np.clip(out, _EPS, 1 - _EPS)

    def normal(self, stream: str, width: int) -> FloatArray:
        return np.asarray(stats.norm.ppf(self.uniform(stream, width)), dtype=np.float64)

    def lognormal(self, stream: str, width: int, sigma: float) -> FloatArray:
        """Mean-one multiplicative noise."""
        return np.exp(sigma * self.normal(stream, width) - 0.5 * sigma**2)


def binomial(n: npt.ArrayLike, p: npt.ArrayLike, u: FloatArray) -> IntArray:
    """Binomial draw by inverse CDF so the same uniform maps to a comparable outcome."""
    n_arr = np.asarray(n, dtype=np.float64)
    p_arr = np.clip(np.asarray(p, dtype=np.float64), 0.0, 1.0)
    draws = stats.binom.ppf(u, n_arr, p_arr)
    return np.where(n_arr > 0, np.nan_to_num(draws), 0.0).astype(np.int64)


def poisson(mean: npt.ArrayLike, u: FloatArray) -> IntArray:
    mu = np.asarray(mean, dtype=np.float64)
    draws = stats.poisson.ppf(u, np.maximum(mu, _EPS))
    return np.where(mu > 0, np.nan_to_num(draws), 0.0).astype(np.int64)
