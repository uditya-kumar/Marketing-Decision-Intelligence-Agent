"""Paid media: budget → spend → CPM → impressions → reach/fatigue → CTR → clicks, per slot."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING

import numpy as np

from novawear_sim.world.arrays import group_sum, normalise_within
from novawear_sim.world.fatigue import exposure_stock, fatigue_multiplier, reach
from novawear_sim.world.rng import FloatArray, IntArray, RandomStreams, binomial
from novawear_sim.world.saturation import efficiency

if TYPE_CHECKING:
    from novawear_sim.world.entities import World
    from novawear_sim.world.festive import CalendarEffects
    from novawear_sim.world.modifiers import Modifiers
    from novawear_sim.world.timeline import Timeline

_SPEND_NOISE = 0.07
_MIX_NOISE = 0.12
_CPM_NOISE = 0.08
_CTR_NOISE = 0.06
_MAX_CTR = 0.5


@dataclass(frozen=True)
class Delivery:
    spend: FloatArray  # (days, slots)
    impressions: IntArray
    reach: FloatArray
    clicks: IntArray
    channel_spend: FloatArray  # (days, channels)
    efficiency: FloatArray  # (days, channels)
    fatigue: FloatArray  # (days, creatives)


def _active(world: World, timeline: Timeline) -> FloatArray:
    """(days, creatives) 1 where the creative is live."""
    out = np.ones((timeline.size, len(world.creatives)))
    for k, creative in enumerate(world.creatives):
        start = creative.active_from or date.min
        end = creative.active_to or date.max
        out[:, k] = timeline.mask(start, end)
    return out


def ad_set_budgets(world: World, timeline: Timeline) -> FloatArray:
    """Planned daily budget per ad set `(days, ad_sets)`: monthly plan split by budget shares."""
    days_in_month = timeline.days_in_month()
    out = np.zeros((timeline.size, len(world.ad_sets)))
    a = 0
    for channel in world.channels:
        daily = (
            np.asarray([channel.monthly_budget.for_month(d.year, d.month) for d in timeline.dates])
            / days_in_month
        )
        campaign_total = sum(c.budget_share for c in channel.campaigns)
        for campaign in channel.campaigns:
            shares = [s.budget_share or 1.0 for s in campaign.ad_sets]
            for share in shares:
                out[:, a] = daily * campaign.budget_share / campaign_total * share / sum(shares)
                a += 1
    return out


def _slot_mix(
    world: World, timeline: Timeline, mods: Modifiers, streams: RandomStreams
) -> FloatArray:
    slots, cfg = world.slots, world.config
    active = _active(world, timeline)
    weights = np.asarray([c.weight for c in world.creatives]) * active
    creative_share = normalise_within(weights, world.creative_ad_set, len(world.ad_sets))
    default_mix = cfg.segments.age_groups
    age_mix = np.asarray(
        [
            [
                (ad_set.age_mix or {a: g.mix for a, g in default_mix.items()})[age]
                for age in world.ages
            ]
            for ad_set in world.ad_sets
        ]
    )
    mobile = np.asarray([ch.mobile_share for ch in world.channels])[slots.channel]
    device_mix = np.where(slots.device == 0, mobile, 1.0 - mobile)
    raw = (
        creative_share[:, slots.creative]
        * age_mix[slots.ad_set, slots.age]
        * device_mix
        * mods.mix
        * streams.lognormal("slot_mix", slots.size, _MIX_NOISE)
    )
    return normalise_within(raw, slots.ad_set, len(world.ad_sets))


def deliver(
    world: World,
    timeline: Timeline,
    mods: Modifiers,
    festive: CalendarEffects,
    demand: FloatArray,
    streams: RandomStreams,
) -> Delivery:
    slots, cfg = world.slots, world.config
    n_ch = len(world.channels)

    budgets = ad_set_budgets(world, timeline) * streams.lognormal(
        "ad_set_spend", len(world.ad_sets), _SPEND_NOISE
    )
    spend = budgets[:, slots.ad_set] * _slot_mix(world, timeline, mods, streams) * mods.spend
    channel_spend = group_sum(spend, slots.channel, n_ch)
    eff = np.column_stack(
        [
            efficiency(channel_spend[:, c], ch.hill, mods.vmax[:, c], mods.k[:, c])
            for c, ch in enumerate(world.channels)
        ]
    )

    ages = [cfg.segments.age_groups[a] for a in world.ages]
    devices = [cfg.segments.devices[d] for d in world.devices]
    festive_sens = np.asarray([ch.festive_cpm_sensitivity for ch in world.channels])
    auction = 1.0 + (festive.cpm[:, None] - 1.0) * festive_sens[None, :]
    cpm = (
        np.asarray([s.cpm for s in world.ad_sets])[slots.ad_set]
        * np.asarray([g.cpm for g in ages])[slots.age]
        * np.asarray([d.cpm for d in devices])[slots.device]
        * auction[:, slots.channel]
        * mods.cpm
        * streams.lognormal("cpm", slots.size, _CPM_NOISE)
    )
    impressions = np.rint(spend / cpm * 1000.0).astype(np.int64)

    creative_impr = group_sum(impressions.astype(np.float64), slots.creative, len(world.creatives))
    audience = (
        np.asarray([world.ad_sets[a].audience_size for a in world.creative_ad_set]) * mods.audience
    )
    sensitivity = np.asarray(
        [
            cfg.fatigue.sensitivity if ch.fatigue_sensitivity is None else ch.fatigue_sensitivity
            for ch in world.channels
        ]
    )[world.creative_channel]
    stock = exposure_stock(creative_impr, audience, cfg.fatigue.memory)
    fatigue = fatigue_multiplier(stock, cfg.fatigue, sensitivity)

    impr_share = np.divide(
        impressions,
        creative_impr[:, slots.creative],
        out=np.zeros_like(creative_impr[:, slots.creative]),
        where=creative_impr[:, slots.creative] > 0,
    )
    slot_reach = reach(impressions.astype(np.float64), audience[:, slots.creative] * impr_share)

    ctr = (
        np.asarray([s.ctr for s in world.ad_sets])[slots.ad_set]
        * np.asarray([c.ctr_factor for c in world.creatives])[slots.creative]
        * np.asarray([g.ctr for g in ages])[slots.age]
        * np.asarray([d.ctr for d in devices])[slots.device]
        * fatigue[:, slots.creative]
        * np.sqrt(eff[:, slots.channel])
        * (demand**cfg.demand_response.ctr)[:, None]
        * mods.ctr
        * streams.lognormal("ctr", slots.size, _CTR_NOISE)
    )
    clicks = binomial(impressions, np.minimum(ctr, _MAX_CTR), streams.uniform("clicks", slots.size))

    return Delivery(
        spend=spend,
        impressions=impressions,
        reach=slot_reach,
        clicks=clicks,
        channel_spend=channel_spend,
        efficiency=eff,
        fatigue=fatigue,
    )
