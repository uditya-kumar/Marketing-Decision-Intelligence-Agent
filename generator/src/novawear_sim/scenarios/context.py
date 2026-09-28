"""What a scenario sees: the world, the timeline, the modifier arrays and targeting helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np
import numpy.typing as npt

from novawear_sim.errors import ScenarioError
from novawear_sim.scenarios.ground_truth import EntityRef
from novawear_sim.world.ids import platform_id

if TYPE_CHECKING:
    from novawear_sim.config.schedule import ScheduledEvent, Target
    from novawear_sim.world.entities import Level, World
    from novawear_sim.world.modifiers import Modifiers
    from novawear_sim.world.rng import FloatArray
    from novawear_sim.world.timeline import Timeline

BoolArray = npt.NDArray[np.bool_]
_LEVELS: tuple[Level, ...] = ("creative", "ad_set", "campaign", "channel")


@dataclass(frozen=True)
class ScenarioContext:
    world: World
    timeline: Timeline
    mods: Modifiers

    def index(self, level: Level, key: str) -> int:
        try:
            return self.world.index_of(level, key)
        except KeyError as exc:
            raise ScenarioError(str(exc)) from exc

    def intensity(self, event: ScheduledEvent, ramp_days: int = 1) -> FloatArray:
        """(days,) 0 outside the event; inside, rises linearly to 1 over `ramp_days`."""
        out = np.zeros(self.timeline.size)
        for i, day in enumerate(self.timeline.dates):
            if event.start <= day <= event.end:
                out[i] = min(1.0, ((day - event.start).days + 1) / max(ramp_days, 1))
        return out

    def slot_mask(self, target: Target) -> BoolArray:
        world, slots = self.world, self.world.slots
        mask = np.ones(slots.size, dtype=bool)
        if target.source is not None:
            sources = np.asarray([ch.source == target.source for ch in world.channels])
            if not sources.any():
                raise ScenarioError(f"unknown source {target.source!r}")
            mask &= sources[slots.channel]
        levels: tuple[tuple[Level, str | None], ...] = (
            ("channel", target.channel),
            ("campaign", target.campaign),
            ("ad_set", target.ad_set),
            ("creative", target.creative),
        )
        for level, key in levels:
            if key is not None:
                mask &= getattr(slots, level) == self.index(level, key)
        if target.device is not None:
            mask &= slots.device == world.devices.index(target.device)
        if target.age_group is not None:
            if target.age_group not in world.ages:
                raise ScenarioError(f"unknown age group {target.age_group!r}")
            mask &= slots.age == world.ages.index(target.age_group)
        return mask

    def describe(self, target: Target) -> EntityRef:
        """Resolve a target to its most specific entity plus the parent chain."""
        world = self.world
        extras = {"device": target.device, "age_group": target.age_group}
        for level in _LEVELS:
            key = getattr(target, level)
            if key is None:
                continue
            idx = self.index(level, key)
            cr_idx = idx if level == "creative" else None
            as_idx = int(world.creative_ad_set[idx]) if cr_idx is not None else None
            as_idx = idx if level == "ad_set" else as_idx
            camp_idx = int(world.ad_set_campaign[as_idx]) if as_idx is not None else None
            camp_idx = idx if level == "campaign" else camp_idx
            ch_idx = int(world.campaign_channel[camp_idx]) if camp_idx is not None else idx
            channel = world.channels[ch_idx]
            creative = world.creatives[cr_idx] if cr_idx is not None else None
            ad_set = world.ad_sets[as_idx] if as_idx is not None else None
            campaign = world.campaigns[camp_idx] if camp_idx is not None else None
            return EntityRef(
                level=level,
                key=key,
                source=channel.source,
                channel=channel.key,
                campaign=campaign.name if campaign else None,
                ad_set=ad_set.name if ad_set else None,
                creative=creative.name if creative else None,
                platform_id=None if level == "channel" else platform_id(channel.source, level, key),
                **extras,
            )
        if target.source is not None:
            self.slot_mask(target)
            return EntityRef(level="source", key=target.source, source=target.source, **extras)
        return EntityRef(level="account", **extras)

    def channels_of(self, ref: EntityRef) -> set[str]:
        """Channels an entity's effects can show up in (used to keep quiet windows clean)."""
        if ref.level == "account":
            return {ch.key for ch in self.world.channels}
        if ref.level == "source":
            return {ch.key for ch in self.world.channels if ch.source == ref.source}
        return {ref.channel} if ref.channel else set()
