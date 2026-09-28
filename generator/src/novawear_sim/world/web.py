"""Web analytics (GA4-like): organic traffic plus paid visitors, as GA4 would record them."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

from novawear_sim.config.models import WEEKDAYS
from novawear_sim.world.arrays import group_sum
from novawear_sim.world.funnel import FunnelCounts, run_funnel
from novawear_sim.world.rng import FloatArray, IntArray, RandomStreams, poisson

if TYPE_CHECKING:
    from novawear_sim.world.entities import World
    from novawear_sim.world.festive import CalendarEffects
    from novawear_sim.world.timeline import Timeline

_CAPTURE_NOISE = 0.01


@dataclass(frozen=True)
class WebTraffic:
    source_medium: tuple[str, ...]  # one per column
    device: tuple[str, ...]
    recorded: FunnelCounts  # (days, columns), after GA4 capture loss


def organic_traffic(
    world: World,
    timeline: Timeline,
    festive: CalendarEffects,
    demand: FloatArray,
    streams: RandomStreams,
) -> tuple[tuple[str, ...], tuple[str, ...], FunnelCounts]:
    cfg = world.config
    sources, devices, expected, intent, engage = [], [], [], [], []
    weekday_names = [WEEKDAYS[w] for w in timeline.weekdays]
    for src in cfg.organic_sources:
        sends = np.asarray(
            [src.send_multiplier if d in src.send_days else 1.0 for d in weekday_names]
        )
        base = src.sessions * sends * demand**cfg.demand_response.sessions
        for device, share in zip(
            world.devices, (src.mobile_share, 1 - src.mobile_share), strict=True
        ):
            sources.append(src.source_medium)
            devices.append(device)
            expected.append(base * share)
            intent.append(src.intent)
            engage.append(cfg.segments.devices[device].engage_rate)

    width = len(sources)
    visitors = poisson(np.column_stack(expected), streams.uniform("organic:visitors", width))
    atc = (
        cfg.funnel.atc_rate
        * np.asarray(intent)[None, :]
        * (demand**cfg.demand_response.conversion)[:, None]
    )
    aov = np.broadcast_to((cfg.funnel.aov * festive.aov)[:, None], visitors.shape)
    counts = run_funnel(
        visitors,
        landing_rate=1.0,
        engage_rate=np.asarray(engage)[None, :],
        atc_rate=atc,
        aov=aov,
        funnel=cfg.funnel,
        streams=streams,
        stream_prefix="organic",
    )
    return tuple(sources), tuple(devices), counts


def _group(counts: FunnelCounts, groups: IntArray, n: int) -> FunnelCounts:
    def g(x: FloatArray | IntArray) -> FloatArray:
        return group_sum(x.astype(np.float64), groups, n)

    return FunnelCounts(
        sessions=g(counts.sessions).astype(np.int64),
        engaged=g(counts.engaged).astype(np.int64),
        add_to_cart=g(counts.add_to_cart).astype(np.int64),
        checkout=g(counts.checkout).astype(np.int64),
        purchases=g(counts.purchases).astype(np.int64),
        revenue=g(counts.revenue),
    )


def _capture(counts: FunnelCounts, rate: FloatArray) -> FunnelCounts:
    # One rate per day/column for every step keeps the recorded funnel monotone.
    def c(x: IntArray) -> IntArray:
        return np.rint(x * rate).astype(np.int64)

    return FunnelCounts(
        sessions=c(counts.sessions),
        engaged=c(counts.engaged),
        add_to_cart=c(counts.add_to_cart),
        checkout=c(counts.checkout),
        purchases=c(counts.purchases),
        revenue=np.round(counts.revenue * rate, 2),
    )


def web_traffic(
    world: World,
    paid: FunnelCounts,
    organic: FunnelCounts,
    organic_sources: tuple[str, ...],
    organic_devices: tuple[str, ...],
    streams: RandomStreams,
) -> WebTraffic:
    slots = world.slots
    n_dev = len(world.devices)
    paid_cols = _group(paid, slots.channel * n_dev + slots.device, len(world.channels) * n_dev)
    sources = tuple(ch.web_source for ch in world.channels for _ in world.devices) + organic_sources
    devices = tuple(d for _ in world.channels for d in world.devices) + organic_devices

    combined = FunnelCounts(
        *(
            np.hstack([getattr(paid_cols, f), getattr(organic, f)])
            for f in ("sessions", "engaged", "add_to_cart", "checkout", "purchases", "revenue")
        )
    )
    rate = np.clip(
        world.config.funnel.ga_capture
        + _CAPTURE_NOISE * streams.normal("ga_capture", len(sources)),
        0.0,
        1.0,
    )
    return WebTraffic(source_medium=sources, device=devices, recorded=_capture(combined, rate))
