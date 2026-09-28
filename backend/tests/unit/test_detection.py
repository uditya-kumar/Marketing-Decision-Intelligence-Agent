"""The whole FR-6 sweep over a small set of facts: what it finds, and what it ignores."""

from __future__ import annotations

import datetime as dt
import math
from typing import Any

import pandas as pd
import pytest

from mdia.domain.detection import Context, Facts, analyse
from mdia.domain.periods import Period, days_in_month, trailing
from mdia.domain.signals import BASELINE_DAYS, WINDOW_DAYS
from mdia.domain.trust import TrackingCheck

pytestmark = pytest.mark.unit

AS_OF = dt.date(2026, 10, 28)
RECENT = trailing(AS_OF, WINDOW_DAYS)
HISTORY = trailing(RECENT.start - dt.timedelta(days=1), BASELINE_DAYS)
SPAN = Period(HISTORY.start, AS_OF)

# One ad set with one creative: enough to move every level above it.
_AD = {
    "channel_id": "meta_ads",
    "campaign_id": 7,
    "campaign_name": "NW | IG | Reels - Festive Edit",
    "ad_set_id": 31,
    "ad_set_name": "Women 18-34 Reels",
    "creative_id": 42,
    "creative_name": "Reel | Get Ready With Me",
    "age_group": "25-34",
    "reach": math.nan,
}
# A steady day: CTR 2 %, CPC ₹20, CPA ₹500, ROAS 6×.
STEADY = {
    "impressions": 50_000.0,
    "clicks": 1_000.0,
    "spend": 20_000.0,
    "platform_conversions": 40.0,
    "platform_revenue": 120_000.0,
}
# Half the clicks and half the conversions for the same spend: CPC and CPA double.
FATIGUED = {**STEADY, "clicks": 500.0, "platform_conversions": 20.0, "platform_revenue": 60_000.0}


def ads(recent: dict[str, float] = STEADY, *, age_groups: int = 1) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for day in SPAN.dates():
        measures = recent if day in RECENT else STEADY
        for index in range(age_groups):
            share = 1 / age_groups
            rows.append(
                {
                    **_AD,
                    "age_group": f"{25 + index * 10}-{34 + index * 10}",
                    "date": day,
                    **{name: value * share for name, value in measures.items()},
                }
            )
    return pd.DataFrame(rows)


def store() -> pd.DataFrame:
    return pd.DataFrame(
        [{"date": day, "store_orders": 100.0, "store_revenue": 400_000.0} for day in SPAN.dates()]
    )


def context(**overrides: Any) -> Context:
    return Context(
        as_of=AS_OF,
        targets=overrides.pop("targets", {}),
        month_budgets=overrides.pop("month_budgets", {"meta_ads": 10_000_000.0}),
        **overrides,
    )


def facts(recent: dict[str, float] = STEADY, **kwargs: Any) -> Facts:
    return Facts(ads=ads(recent, **kwargs), web=pd.DataFrame(), store=store())


def test_a_tired_creative_is_one_opportunity_on_the_creative() -> None:
    found = analyse(facts(FATIGUED), context())

    assert len(found) == 1
    opportunity = found[0]
    assert opportunity.key == "creative:42"
    assert opportunity.kind == "issue"
    assert opportunity.entity.name == "Reel | Get Ready With Me"
    assert opportunity.entity.ancestors == (
        "account:all",
        "channel:meta_ads",
        "campaign:7",
        "ad_set:31",
    )
    # ROAS halving on the week's spend is the biggest number in the group.
    assert opportunity.primary_metric == "roas"
    assert {s.metric for s in opportunity.signals} == {"roas", "cpa", "cpc", "ctr"}
    assert opportunity.impact == pytest.approx(3 * 140_000)


def test_a_quiet_week_produces_nothing() -> None:
    assert analyse(facts(), context()) == []


def test_an_age_group_out_of_line_with_its_peers_is_found() -> None:
    frame = pd.concat(
        [
            ads(age_groups=2),
            # A third age group in the same ad set, spending the same for half the sales.
            ads(age_groups=1).assign(age_group="45-54", platform_conversions=20.0),
        ]
    )
    found = analyse(Facts(ads=frame, web=pd.DataFrame(), store=store()), context())

    keys = {o.key for o in found}
    assert "age_group:31|45-54" in keys
    segment = next(o for o in found if o.key == "age_group:31|45-54")
    assert segment.primary.detector == "segment_divergence"
    assert segment.entity.ancestors[-1] == "ad_set:31"


def test_overspending_a_channel_budget_is_an_opportunity() -> None:
    # Half of what the month would cost at the week's spend rate.
    budget = 20_000.0 * days_in_month(AS_OF) / 2
    found = analyse(facts(), context(month_budgets={"meta_ads": budget}))

    assert [(o.key, o.primary_metric) for o in found] == [("channel:meta_ads", "spend")]
    assert found[0].primary.detector == "goal_breach"


def test_a_channel_on_pace_mid_month_is_left_alone() -> None:
    # The budget buys the whole month at this rate, not the part of it that has run.
    budget = 20_000.0 * days_in_month(AS_OF)

    assert analyse(facts(), context(month_budgets={"meta_ads": budget})) == []


def test_a_broken_channel_keeps_only_what_the_pixel_cannot_break() -> None:
    check = TrackingCheck("broken", 0.16, dt.date(2026, 10, 24), -81.2, -10.2)
    found = analyse(
        facts(FATIGUED),
        context(tracking={"meta_ads": check}, broken=["meta_ads"]),
    )

    assert [(o.key, o.primary.detector) for o in found] == [
        ("channel:meta_ads", "tracking_break"),
        # Impressions, clicks and spend still arrive, so the tired creative is still real.
        ("creative:42", "baseline_change"),
    ]
    assert {s.metric for s in found[1].signals} == {"cpc", "ctr"}


def test_festive_weeks_are_left_alone() -> None:
    festive = [Period(dt.date(2026, 10, 20), dt.date(2026, 11, 5))]

    assert analyse(facts(FATIGUED), context(festive=festive)) == []


def test_a_missed_account_target_is_an_opportunity() -> None:
    found = analyse(facts(), context(targets={"mer": 25.0}))

    assert [(o.key, o.primary_metric) for o in found] == [("account:all", "mer")]


def test_a_funnel_step_collapse_is_found_per_channel() -> None:
    def web(day: dt.date) -> list[dict[str, Any]]:
        broken = day in RECENT
        return [
            {
                "date": day,
                "source": "facebook / paid_social",
                "sessions": 5_000.0,
                "bounces": 2_000.0,
                "add_to_cart": 250.0 if broken else 500.0,
                "checkout": 100.0 if broken else 200.0,
                "purchases": 50.0 if broken else 100.0,
            },
            # Organic sessions are unaffected and belong to no channel.
            {
                "date": day,
                "source": "google / organic",
                "sessions": 4_000.0,
                "bounces": 1_600.0,
                "add_to_cart": 400.0,
                "checkout": 160.0,
                "purchases": 80.0,
            },
        ]

    frame = pd.DataFrame([row for day in SPAN.dates() for row in web(day)])
    found = analyse(Facts(ads=ads(), web=frame, store=store()), context())

    assert [(o.key, o.primary_metric) for o in found] == [("channel:meta_ads", "atc_rate")]
    assert found[0].primary.detector == "funnel_drop"
