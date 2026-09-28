"""Paid traffic outcomes per slot: site funnel from ad clicks + platform-reported conversions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

from novawear_sim.world.funnel import FunnelCounts, run_funnel
from novawear_sim.world.rng import FloatArray, RandomStreams, poisson

if TYPE_CHECKING:
    from novawear_sim.world.entities import World
    from novawear_sim.world.festive import CalendarEffects
    from novawear_sim.world.media import Delivery
    from novawear_sim.world.modifiers import Modifiers

_GOOGLE_CREDIT_NOISE = 0.15
_VALUE_NOISE = 0.1


@dataclass(frozen=True)
class PaidOutcome:
    funnel: FunnelCounts  # true on-site behaviour of ad visitors
    platform_conversions: FloatArray  # what the ad platform claims (fractional for Google DDA)
    platform_revenue: FloatArray


def paid_outcome(
    world: World,
    delivery: Delivery,
    mods: Modifiers,
    festive: CalendarEffects,
    demand: FloatArray,
    streams: RandomStreams,
) -> PaidOutcome:
    slots, cfg = world.slots, world.config
    engage = np.asarray([cfg.segments.devices[d].engage_rate for d in world.devices])[slots.device]
    intent = (
        np.asarray([s.intent for s in world.ad_sets])[slots.ad_set]
        * np.asarray([cfg.segments.age_groups[a].intent for a in world.ages])[slots.age]
    )
    atc = (
        cfg.funnel.atc_rate
        * intent
        * (demand**cfg.demand_response.conversion)[:, None]
        * np.sqrt(delivery.efficiency[:, slots.channel])
        * mods.atc
    )
    aov = np.broadcast_to((cfg.funnel.aov * festive.aov)[:, None], delivery.clicks.shape)
    funnel = run_funnel(
        delivery.clicks,
        landing_rate=cfg.funnel.landing_rate,
        engage_rate=engage * mods.engage,
        atc_rate=atc,
        aov=aov,
        funnel=cfg.funnel,
        streams=streams,
        stream_prefix="paid",
    )

    ratio = np.asarray([ch.attribution_ratio for ch in world.channels])[slots.channel]
    claimed_mean = funnel.purchases * ratio * mods.attribution
    is_google = np.asarray([ch.source == "google_ads" for ch in world.channels])[slots.channel]
    google = np.round(
        claimed_mean * streams.lognormal("google_credit", slots.size, _GOOGLE_CREDIT_NOISE), 2
    )
    meta = poisson(claimed_mean, streams.uniform("meta_credit", slots.size)).astype(np.float64)
    conversions = np.where(is_google, google, meta)

    value_per_order = np.divide(
        funnel.revenue, funnel.purchases, out=aov.copy(), where=funnel.purchases > 0
    )
    revenue = np.round(
        conversions
        * value_per_order
        * streams.lognormal("platform_value", slots.size, _VALUE_NOISE),
        2,
    )
    return PaidOutcome(funnel=funnel, platform_conversions=conversions, platform_revenue=revenue)
