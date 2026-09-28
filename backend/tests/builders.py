"""Opportunities shaped like the seven generator scenarios, for the agent-side tests.

Real measures, so the evidence tree is genuinely decomposed rather than stubbed: each
scenario's "after" numbers are the ones that make its cause the arithmetic story.
"""

from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING

from mdia.domain.kpi import kpis
from mdia.domain.opportunities import Opportunity
from mdia.domain.periods import trailing
from mdia.domain.signals import WINDOW_DAYS, Entity, Signal, signal_id

if TYPE_CHECKING:
    from collections.abc import Mapping

    from mdia.domain.kpi import Metric
    from mdia.domain.opportunities import OpportunityKind
    from mdia.domain.signals import Detector

AS_OF = dt.date(2026, 10, 28)
WINDOW = trailing(AS_OF, WINDOW_DAYS)

ACCOUNT = Entity("account", "all", "NovaWear")
CHANNEL = Entity("channel", "meta_ads", "Meta Ads", "meta_ads", ("account:all",))
CAMPAIGN = Entity(
    "campaign", "7", "NW | IG | Reels", "meta_ads", ("account:all", "channel:meta_ads")
)
CREATIVE = Entity(
    "creative",
    "42",
    "Reel | Get Ready With Me",
    "meta_ads",
    ("account:all", "channel:meta_ads", "campaign:7", "ad_set:31"),
)
SEGMENT = Entity(
    "age_group",
    "31:25-34",
    "25-34",
    "meta_ads",
    ("account:all", "channel:meta_ads", "campaign:7", "ad_set:31"),
)

# A normal week: CTR 1.5 %, CPC ₹20, CVR 3 %, CPA ₹666, ROAS 4.5x.
BASELINE: Mapping[str, float] = {
    "impressions": 1_000_000.0,
    "clicks": 15_000.0,
    "spend": 300_000.0,
    "platform_conversions": 450.0,
    "platform_revenue": 1_350_000.0,
}


def signal(
    detector: Detector,
    metric: Metric,
    entity: Entity = CHANNEL,
    *,
    current: float | None = None,
    baseline: float | None = None,
    after: Mapping[str, float] | None = None,
    adverse: bool = True,
    score: float = 10_000.0,
) -> Signal:
    """One signal, with its values read off ``after`` and ``BASELINE`` when not given."""
    measures = dict(after or {})
    values = kpis(measures) if measures else {}
    before = kpis(BASELINE)
    return Signal(
        id=signal_id(detector, entity, metric, WINDOW),
        detector=detector,
        metric=metric,
        entity=entity,
        window=WINDOW,
        current=current if current is not None else values.get(metric),  # type: ignore[arg-type]
        baseline=baseline if baseline is not None else before.get(metric),  # type: ignore[arg-type]
        change_pct=_change(metric, current, baseline, values, before),
        adverse=adverse,
        measures=measures,
        baseline_measures=dict(BASELINE) if measures else {},
        impact=score * 2,
        score=score,
    )


def opportunity(
    entity: Entity, signals: tuple[Signal, ...], *, kind: OpportunityKind = "issue"
) -> Opportunity:
    primary = max(signals, key=lambda item: item.score)
    return Opportunity(
        key=f"{entity.id}|{WINDOW.end:%Y%m%d}",
        kind=kind,
        entity=entity,
        window=WINDOW,
        primary=primary,
        signals=signals,
        impact=primary.impact,
        score=primary.score,
    )


def creative_fatigue() -> Opportunity:
    """CTR collapses on a tired creative; CPM holds, so CPC and CPA follow it up."""
    after = _after(clicks=9_000.0, platform_conversions=270.0, platform_revenue=810_000.0)
    return opportunity(
        CREATIVE,
        (
            signal("baseline_change", "cpa", CREATIVE, after=after, score=60_000.0),
            signal("baseline_change", "ctr", CREATIVE, after=after, score=40_000.0),
            signal("baseline_change", "frequency", CREATIVE, current=4.2, baseline=3.1),
        ),
    )


def cpc_spike() -> Opportunity:
    """The auction gets dearer: CPM doubles with CTR unchanged."""
    after = _after(
        impressions=500_000.0,
        clicks=7_500.0,
        platform_conversions=225.0,
        platform_revenue=675_000.0,
    )
    return opportunity(
        CHANNEL,
        (
            signal("baseline_change", "cpa", CHANNEL, after=after, score=90_000.0),
            signal("baseline_change", "cpm", CHANNEL, after=after, score=50_000.0),
        ),
    )


def landing_page_break() -> Opportunity:
    """Clicks are as cheap as ever, but half of them no longer convert."""
    after = _after(platform_conversions=225.0, platform_revenue=675_000.0)
    return opportunity(
        CHANNEL,
        (
            signal("baseline_change", "cpa", CHANNEL, after=after, score=80_000.0),
            signal("funnel_drop", "atc_rate", CHANNEL, current=0.021, baseline=0.038),
        ),
    )


def audience_mismatch() -> Opportunity:
    """One age group inside the ad set is doing the damage."""
    after = _after(platform_conversions=250.0, platform_revenue=750_000.0)
    return opportunity(
        SEGMENT,
        (
            signal("baseline_change", "cpa", SEGMENT, after=after, score=45_000.0),
            signal("segment_divergence", "cpa", SEGMENT, current=1_200.0, baseline=700.0),
        ),
    )


def tracking_break() -> Opportunity:
    """Reported conversions fall away from store orders: the pixel, not the ads."""
    return opportunity(
        CHANNEL,
        (signal("tracking_break", "platform_conversions", CHANNEL, current=0.42, baseline=1.0),),
    )


def budget_overpace() -> Opportunity:
    """Daily spend is running ahead of what the month's budget allows."""
    return opportunity(
        CHANNEL,
        (signal("goal_breach", "spend", CHANNEL, current=50_000.0, baseline=35_000.0),),
    )


def channel_opportunity() -> Opportunity:
    """A channel beating its own baseline at flat spend: room to buy more."""
    after = _after(platform_conversions=600.0, platform_revenue=1_950_000.0)
    return opportunity(
        CHANNEL,
        (signal("baseline_change", "roas", CHANNEL, after=after, adverse=False, score=70_000.0),),
        kind="win",
    )


SCENARIOS = {
    "creative_fatigue": creative_fatigue,
    "cpc_spike": cpc_spike,
    "landing_page_break": landing_page_break,
    "audience_mismatch": audience_mismatch,
    "tracking_break": tracking_break,
    "budget_overpace": budget_overpace,
    "channel_opportunity": channel_opportunity,
}


def _after(**changed: float) -> dict[str, float]:
    return dict(BASELINE) | changed


def _change(
    metric: Metric,
    current: float | None,
    baseline: float | None,
    values: Mapping[str, float | None],
    before: Mapping[str, float | None],
) -> float | None:
    now = current if current is not None else values.get(metric)
    then = baseline if baseline is not None else before.get(metric)
    if now is None or not then:
        return None
    return (now - then) / abs(then) * 100
