"""Metric decomposition (FR-4.4): which driver moved a KPI, by log-change attribution.

A KPI that is a product of drivers, ``M = Π dᵢ^eᵢ``, satisfies
``ln(M₁/M₀) = Σ eᵢ · ln(dᵢ₁/dᵢ₀)``, so each driver's share of the change is its term
over the total. Shares always sum to 100 %; a driver that pulled the other way gets
a negative share, which is what lets the evidence tree say "despite".
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping

    from mdia.domain.kpi import Kpi, Metric

# Exponent of each driver; the constant 1000 in CPC = CPM / (1000·CTR) cancels in a ratio.
FORMULAS: dict[Kpi, dict[Kpi, int]] = {
    "cpa": {"cpc": 1, "cvr": -1},
    "roas": {"cvr": 1, "aov": 1, "cpc": -1},
    "cpc": {"cpm": 1, "ctr": -1},
}


@dataclass(frozen=True, slots=True)
class Driver:
    metric: Kpi
    before: float
    after: float
    change_pct: float
    share_pct: float


@dataclass(frozen=True, slots=True)
class Decomposition:
    metric: Kpi
    before: float
    after: float
    change_pct: float
    drivers: list[Driver]


def decompose(
    metric: Kpi,
    before: Mapping[Metric, float | None],
    after: Mapping[Metric, float | None],
) -> Decomposition | None:
    """Attribute the change in ``metric`` to its drivers.

    ``None`` when a value is missing or not positive (a log needs both sides > 0), or
    when the metric didn't move, since there is then no change to share out.
    """
    formula = FORMULAS[metric]
    pairs: dict[Kpi, tuple[float, float]] = {}
    for m in (metric, *formula):
        b, a = before.get(m), after.get(m)
        if b is None or a is None or b <= 0 or a <= 0:
            return None
        pairs[m] = (b, a)
    terms = {m: e * math.log(pairs[m][1] / pairs[m][0]) for m, e in formula.items()}
    total = sum(terms.values())
    if math.isclose(total, 0.0, abs_tol=1e-12):
        return None
    drivers = [
        Driver(
            metric=m,
            before=pairs[m][0],
            after=pairs[m][1],
            change_pct=(pairs[m][1] / pairs[m][0] - 1) * 100,
            share_pct=term / total * 100,
        )
        for m, term in terms.items()
    ]
    before_value, after_value = pairs[metric]
    change = (after_value / before_value - 1) * 100
    return Decomposition(metric, before_value, after_value, change, drivers)
