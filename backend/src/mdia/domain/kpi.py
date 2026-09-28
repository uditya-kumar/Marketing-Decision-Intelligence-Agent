"""KPIs (FR-4.1, FR-4.2): every ratio is recomputed from summed base measures.

Averaging daily ratios would weight a quiet day like a busy one, so callers sum the
base measures over whatever slice they need and only then call :func:`kpis`. The
same definitions drive the vectorised :func:`add_kpis` used for daily series.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, get_args

if TYPE_CHECKING:
    from collections.abc import Mapping

    import pandas as pd

Kpi = Literal[
    "ctr", "cpc", "cpm", "cvr", "cpa", "roas", "aov", "frequency", "mer", "store_aov",
    # Web funnel steps, each a rate on the step above it (FR-6.1 funnel detector).
    "bounce_rate", "atc_rate", "checkout_rate", "purchase_rate", "web_cvr",
]  # fmt: skip

# Base measures that are shown as metrics in their own right.
Measure = Literal[
    "impressions", "clicks", "spend", "platform_conversions", "platform_revenue",
    "store_revenue", "store_orders",
]  # fmt: skip
Metric = Kpi | Measure
METRICS: tuple[Metric, ...] = (*get_args(Kpi), *get_args(Measure))

# Ways an ad metric can be sliced (FR-4.3).
Dimension = Literal["channel", "campaign", "ad_set", "creative", "age_group"]


@dataclass(frozen=True, slots=True)
class KpiDef:
    numerator: str
    denominator: str
    higher_is_better: bool
    scale: float = 1.0


# Measure names match the fact columns; store measures carry a ``store_`` prefix so
# they can sit next to the platform-reported ones in one row.
KPI_DEFS: dict[Kpi, KpiDef] = {
    "ctr": KpiDef("clicks", "impressions", higher_is_better=True),
    "cpc": KpiDef("spend", "clicks", higher_is_better=False),
    "cpm": KpiDef("spend", "impressions", higher_is_better=False, scale=1000),
    "cvr": KpiDef("platform_conversions", "clicks", higher_is_better=True),
    "cpa": KpiDef("spend", "platform_conversions", higher_is_better=False),
    "roas": KpiDef("platform_revenue", "spend", higher_is_better=True),
    # Platform value per conversion: the AOV term in ROAS = CVR × AOV / CPC.
    "aov": KpiDef("platform_revenue", "platform_conversions", higher_is_better=True),
    "frequency": KpiDef("impressions", "reach", higher_is_better=False),
    "bounce_rate": KpiDef("bounces", "sessions", higher_is_better=False),
    "atc_rate": KpiDef("add_to_cart", "sessions", higher_is_better=True),
    "checkout_rate": KpiDef("checkout", "add_to_cart", higher_is_better=True),
    "purchase_rate": KpiDef("purchases", "checkout", higher_is_better=True),
    # The whole web funnel in one number, for comparing channels.
    "web_cvr": KpiDef("purchases", "sessions", higher_is_better=True),
    # Marketing efficiency ratio: what the store really took per rupee of ad spend.
    "mer": KpiDef("store_revenue", "spend", higher_is_better=True),
    "store_aov": KpiDef("store_revenue", "store_orders", higher_is_better=True),
}


# Spend is neither good nor bad on its own, so its change gets no direction.
_MEASURE_DIRECTION: dict[Measure, bool | None] = {
    "impressions": True,
    "clicks": True,
    "spend": None,
    "platform_conversions": True,
    "platform_revenue": True,
    "store_revenue": True,
    "store_orders": True,
}


def definition(metric: Metric) -> KpiDef | None:
    """How ``metric`` is computed, or ``None`` when it is a base measure."""
    return KPI_DEFS.get(metric)  # type: ignore[arg-type]


def higher_is_better(metric: Metric) -> bool | None:
    if metric in KPI_DEFS:
        return KPI_DEFS[metric].higher_is_better
    return _MEASURE_DIRECTION[metric]  # type: ignore[index]


def ratio(numerator: float | None, denominator: float | None, scale: float = 1.0) -> float | None:
    """``numerator / denominator``; ``None`` when either side is missing or the base is 0."""
    if numerator is None or denominator is None or denominator == 0:
        return None
    if math.isnan(numerator) or math.isnan(denominator):
        return None
    return float(numerator) / float(denominator) * scale


def kpis(measures: Mapping[str, float | None]) -> dict[Kpi, float | None]:
    """Every KPI whose base measures are present in ``measures``."""
    return {
        name: ratio(measures[d.numerator], measures[d.denominator], d.scale)
        for name, d in KPI_DEFS.items()
        if d.numerator in measures and d.denominator in measures
    }


def metric_values(measures: Mapping[str, float | None]) -> dict[Metric, float | None]:
    """The measures themselves plus every KPI they allow; absent metrics are ``None``."""
    values: dict[Metric, float | None] = dict.fromkeys(METRICS)
    values.update({m: _clean(measures[m]) for m in get_args(Measure) if m in measures})
    return values | kpis(measures)


def _clean(value: float | None) -> float | None:
    return None if value is None or math.isnan(value) else float(value)


def add_kpis(frame: pd.DataFrame) -> pd.DataFrame:
    """Return ``frame`` with a column per KPI its measure columns allow (NaN on a 0 base)."""
    out = frame.copy()
    for name, d in KPI_DEFS.items():
        if d.numerator in frame and d.denominator in frame:
            base = frame[d.denominator].astype(float)
            out[name] = frame[d.numerator].astype(float) / base.where(base != 0) * d.scale
    return out


def change_pct(previous: float | None, current: float | None) -> float | None:
    """Relative change in %, or ``None`` when there's no usable previous value."""
    if previous is None or current is None or previous == 0:
        return None
    return (current - previous) / abs(previous) * 100
