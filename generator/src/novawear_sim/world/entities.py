"""Flatten the world config into indexed entities and the ad "slot" grid.

A slot is one exported ad row per day: creative × age group × device. Every array in the
simulation is shaped `(days, slots)` (or `(days, creatives|channels)`), so scenarios can target
any slice with a boolean mask.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

import numpy as np
import numpy.typing as npt

from novawear_sim.config.models import DEVICES, Device, WorldConfig

if TYPE_CHECKING:
    from novawear_sim.config.channels import AdSet, Campaign, Channel, Creative

IntArray = npt.NDArray[np.int64]
Level = Literal["channel", "campaign", "ad_set", "creative"]


@dataclass(frozen=True)
class Slots:
    creative: IntArray
    ad_set: IntArray
    campaign: IntArray
    channel: IntArray
    age: IntArray
    device: IntArray

    @property
    def size(self) -> int:
        return int(self.creative.size)


@dataclass(frozen=True)
class World:
    config: WorldConfig
    channels: tuple[Channel, ...]
    campaigns: tuple[Campaign, ...]
    ad_sets: tuple[AdSet, ...]
    creatives: tuple[Creative, ...]
    campaign_channel: IntArray
    ad_set_campaign: IntArray
    ad_set_channel: IntArray
    creative_ad_set: IntArray
    creative_channel: IntArray
    ages: tuple[str, ...]
    devices: tuple[Device, ...]
    slots: Slots

    def index_of(self, level: Level, key: str) -> int:
        keys = {
            "channel": [c.key for c in self.channels],
            "campaign": [c.key for c in self.campaigns],
            "ad_set": [a.key for a in self.ad_sets],
            "creative": [c.key for c in self.creatives],
        }[level]
        if key not in keys:
            raise KeyError(f"unknown {level} {key!r}")
        return keys.index(key)


def build_world(config: WorldConfig) -> World:
    campaigns: list[Campaign] = []
    ad_sets: list[AdSet] = []
    creatives: list[Creative] = []
    campaign_channel: list[int] = []
    ad_set_campaign: list[int] = []
    creative_ad_set: list[int] = []

    for ch_idx, channel in enumerate(config.channels):
        for campaign in channel.campaigns:
            campaign_channel.append(ch_idx)
            campaigns.append(campaign)
            for ad_set in campaign.ad_sets:
                ad_set_campaign.append(len(campaigns) - 1)
                ad_sets.append(ad_set)
                for creative in ad_set.creatives:
                    creative_ad_set.append(len(ad_sets) - 1)
                    creatives.append(creative)

    camp_ch = np.asarray(campaign_channel, dtype=np.int64)
    as_camp = np.asarray(ad_set_campaign, dtype=np.int64)
    cr_as = np.asarray(creative_ad_set, dtype=np.int64)
    ages = tuple(config.segments.age_groups)

    n_cr, n_age, n_dev = len(creatives), len(ages), len(DEVICES)
    cr, age, dev = (
        g.ravel()
        for g in np.meshgrid(np.arange(n_cr), np.arange(n_age), np.arange(n_dev), indexing="ij")
    )
    slots = Slots(
        creative=cr.astype(np.int64),
        ad_set=cr_as[cr],
        campaign=as_camp[cr_as[cr]],
        channel=camp_ch[as_camp[cr_as[cr]]],
        age=age.astype(np.int64),
        device=dev.astype(np.int64),
    )
    return World(
        config=config,
        channels=tuple(config.channels),
        campaigns=tuple(campaigns),
        ad_sets=tuple(ad_sets),
        creatives=tuple(creatives),
        campaign_channel=camp_ch,
        ad_set_campaign=as_camp,
        ad_set_channel=camp_ch[as_camp],
        creative_ad_set=cr_as,
        creative_channel=camp_ch[as_camp[cr_as]],
        ages=ages,
        devices=DEVICES,
        slots=slots,
    )
