"""Decomposition: identities hold and driver shares always add up to 100 %."""

from __future__ import annotations

import math

import pytest
from hypothesis import assume, given
from hypothesis import strategies as st

from mdia.domain.decomposition import FORMULAS, decompose
from mdia.domain.kpi import kpis

pytestmark = pytest.mark.unit

positive = st.floats(min_value=1, max_value=1e6, allow_nan=False)


@st.composite
def ad_totals(draw: st.DrawFn) -> dict[str, float]:
    impressions = draw(st.floats(min_value=1_000, max_value=1e7))
    clicks = draw(st.floats(min_value=10, max_value=impressions / 2))
    return {
        "impressions": impressions,
        "clicks": clicks,
        "spend": draw(positive),
        "platform_conversions": draw(st.floats(min_value=1, max_value=clicks)),
        "platform_revenue": draw(positive),
    }


def test_cpa_rise_driven_by_falling_conversion_rate() -> None:
    before = {"cpa": 420.0, "cpc": 21.0, "cvr": 0.05}
    after = {"cpa": 610.0, "cpc": 21.84, "cvr": 21.84 / 610}

    result = decompose("cpa", before, after)

    assert result is not None
    assert result.change_pct == pytest.approx(45.24, abs=0.01)
    shares = {d.metric: d.share_pct for d in result.drivers}
    assert shares["cvr"] > 85
    assert shares["cpc"] == pytest.approx(100 - shares["cvr"])
    cvr = next(d for d in result.drivers if d.metric == "cvr")
    assert cvr.change_pct < 0


@given(st.sampled_from(sorted(FORMULAS)), ad_totals(), ad_totals())
def test_identities_hold_and_shares_sum_to_100(
    metric: str, a: dict[str, float], b: dict[str, float]
) -> None:
    before, after = kpis(a), kpis(b)
    result = decompose(metric, before, after)  # type: ignore[arg-type]
    assume(result is not None)
    assert result is not None

    assert sum(d.share_pct for d in result.drivers) == pytest.approx(100)
    log_change = math.log(result.after / result.before)
    exponents = FORMULAS[result.metric]
    explained = sum(exponents[d.metric] * math.log(d.after / d.before) for d in result.drivers)
    assert explained == pytest.approx(log_change, abs=1e-9)


def test_offsetting_driver_gets_a_negative_share() -> None:
    before = {"cpa": 400.0, "cpc": 20.0, "cvr": 0.05}
    after = {"cpa": 480.0, "cpc": 16.0, "cvr": 16 / 480}

    result = decompose("cpa", before, after)

    assert result is not None
    shares = {d.metric: d.share_pct for d in result.drivers}
    assert shares["cpc"] < 0 < 100 < shares["cvr"]


@pytest.mark.parametrize(
    "after",
    [
        {"cpa": 400.0, "cpc": 20.0, "cvr": 0.05},
        {"cpa": 400.0, "cpc": None, "cvr": 0.05},
        {"cpa": 0.0, "cpc": 20.0, "cvr": 0.05},
    ],
)
def test_no_decomposition_without_a_change_or_valid_values(after: dict) -> None:
    before = {"cpa": 400.0, "cpc": 20.0, "cvr": 0.05}
    assert decompose("cpa", before, after) is None
