"""KPI maths: safe ratios, ratio-of-sums aggregation and the vectorised series."""

from __future__ import annotations

import math

import pandas as pd
import pytest
from hypothesis import given
from hypothesis import strategies as st

from mdia.domain.kpi import (
    KPI_DEFS,
    METRICS,
    add_kpis,
    change_pct,
    higher_is_better,
    kpis,
    metric_values,
    ratio,
)

pytestmark = pytest.mark.unit

counts = st.integers(min_value=0, max_value=10**7)
# Rupee amounts carry paise precision, so no subnormal floats.
money = st.integers(min_value=0, max_value=10**10).map(lambda paise: paise / 100)


@st.composite
def ad_day(draw: st.DrawFn) -> dict[str, float]:
    impressions = draw(counts)
    clicks = draw(st.integers(min_value=0, max_value=impressions))
    return {
        "impressions": impressions,
        "reach": draw(st.integers(min_value=0, max_value=impressions)),
        "clicks": clicks,
        "spend": draw(money),
        "platform_conversions": draw(st.integers(min_value=0, max_value=clicks * 100)) / 100,
        "platform_revenue": draw(money),
        "store_revenue": draw(money),
        "store_orders": draw(counts),
    }


def test_kpis_from_a_hand_worked_day() -> None:
    day = {
        "impressions": 20_000,
        "reach": 8_000,
        "clicks": 400,
        "spend": 12_000.0,
        "platform_conversions": 20.0,
        "platform_revenue": 48_000.0,
        "store_revenue": 60_000.0,
        "store_orders": 25,
    }

    assert kpis(day) == pytest.approx(
        {
            "ctr": 0.02,
            "cpc": 30.0,
            "cpm": 600.0,
            "cvr": 0.05,
            "cpa": 600.0,
            "roas": 4.0,
            "aov": 2400.0,
            "frequency": 2.5,
            "mer": 5.0,
            "store_aov": 2400.0,
        }
    )


def test_only_kpis_with_their_measures_present_are_returned() -> None:
    assert kpis({"sessions": 200, "bounces": 90}) == {"bounce_rate": pytest.approx(0.45)}


@given(ad_day())
def test_kpis_never_divide_by_zero(day: dict[str, float]) -> None:
    for name, value in kpis(day).items():
        base = day[KPI_DEFS[name].denominator]
        assert (value is None) == (base == 0)
        assert value is None or math.isfinite(value)


@given(ad_day(), ad_day())
def test_aggregate_kpi_is_the_ratio_of_sums_not_the_mean_of_ratios(
    a: dict[str, float], b: dict[str, float]
) -> None:
    total = {key: a[key] + b[key] for key in a}

    for name, value in kpis(total).items():
        d = KPI_DEFS[name]
        expected = ratio(a[d.numerator] + b[d.numerator], a[d.denominator] + b[d.denominator])
        if expected is None:
            assert value is None
        else:
            assert value == pytest.approx(expected * d.scale)


def test_the_mean_of_daily_ratios_would_be_wrong() -> None:
    quiet = {"spend": 100.0, "platform_revenue": 1_000.0}
    busy = {"spend": 10_000.0, "platform_revenue": 20_000.0}
    both = {key: quiet[key] + busy[key] for key in quiet}

    assert kpis(both)["roas"] == pytest.approx(21_000 / 10_100)
    assert kpis(both)["roas"] != pytest.approx((10 + 2) / 2)


@given(st.lists(ad_day(), min_size=1, max_size=5))
def test_series_matches_the_scalar_definition(days: list[dict[str, float]]) -> None:
    frame = add_kpis(pd.DataFrame(days))

    for i, day in enumerate(days):
        for name, value in kpis(day).items():
            cell = frame.loc[i, name]
            if value is None:
                assert math.isnan(cell)
            else:
                assert cell == pytest.approx(value)


@pytest.mark.parametrize(
    ("previous", "current", "expected"),
    [(100, 106, 6.0), (500, 428, -14.4), (0, 5, None), (None, 5, None), (-10, -5, 50.0)],
)
def test_change_pct(previous: float | None, current: float, expected: float | None) -> None:
    assert change_pct(previous, current) == pytest.approx(expected)


def test_metric_values_cover_every_metric_and_blank_what_cannot_be_computed() -> None:
    values = metric_values({"spend": 1_000.0, "platform_conversions": 4.0, "clicks": math.nan})

    assert values.keys() == set(METRICS)
    assert values["spend"] == 1_000.0
    assert values["cpa"] == 250.0
    assert values["clicks"] is None
    assert values["cpc"] is None
    assert values["mer"] is None


def test_direction_of_each_metric() -> None:
    assert higher_is_better("roas") is True
    assert higher_is_better("cpa") is False
    assert higher_is_better("store_revenue") is True
    assert higher_is_better("spend") is None
