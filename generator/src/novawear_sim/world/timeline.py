"""The simulated date axis."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from novawear_sim.world.rng import IntArray


@dataclass(frozen=True)
class Timeline:
    dates: tuple[date, ...]

    @classmethod
    def between(cls, start: date, end: date) -> Timeline:
        return cls(tuple(start + timedelta(days=i) for i in range((end - start).days + 1)))

    @property
    def size(self) -> int:
        return len(self.dates)

    @property
    def ordinals(self) -> IntArray:
        return np.asarray([d.toordinal() for d in self.dates], dtype=np.int64)

    @property
    def weekdays(self) -> IntArray:
        return np.asarray([d.weekday() for d in self.dates], dtype=np.int64)

    def mask(self, start: date, end: date) -> np.ndarray:
        """Boolean `(days,)` mask for the inclusive window."""
        return np.asarray([start <= d <= end for d in self.dates], dtype=bool)

    def days_in_month(self) -> IntArray:
        out = []
        for d in self.dates:
            nxt = date(d.year + (d.month == 12), d.month % 12 + 1, 1)
            out.append((nxt - date(d.year, d.month, 1)).days)
        return np.asarray(out, dtype=np.int64)
