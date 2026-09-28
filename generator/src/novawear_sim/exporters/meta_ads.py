"""`meta_ads.csv` — shaped like a Meta Ads Manager export (Facebook + Instagram placements)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

from novawear_sim.exporters.common import ad_rows, entity_columns, row_dates

if TYPE_CHECKING:
    from datetime import date

    from novawear_sim.engine import Simulation

SOURCE = "meta_ads"
DEVICE_LABELS = {"mobile": "Mobile app", "desktop": "Desktop"}
COLUMNS = [
    "Reporting starts",
    "Reporting ends",
    "Campaign name",
    "Campaign ID",
    "Ad set name",
    "Ad set ID",
    "Ad name",
    "Ad ID",
    "Platform",
    "Age",
    "Device platform",
    "Region",
    "Amount spent (INR)",
    "Impressions",
    "Reach",
    "Frequency",
    "Link clicks",
    "Purchases",
    "Purchases conversion value",
]


def meta_ads_frame(sim: Simulation, start: date, end: date) -> pd.DataFrame:
    rows = ad_rows(sim, SOURCE, start, end)
    world, slots = sim.world, sim.world.slots
    names = entity_columns(sim, rows, SOURCE)
    days = [d.isoformat() for d in row_dates(sim, rows)]
    impressions = rows.take(sim.delivery.impressions).astype(np.int64)
    reach = np.clip(np.rint(rows.take(sim.delivery.reach).astype(np.float64)), 1, impressions)
    return pd.DataFrame(
        {
            "Reporting starts": days,
            "Reporting ends": days,
            "Campaign name": names["campaign"],
            "Campaign ID": names["campaign_id"],
            "Ad set name": names["ad_set"],
            "Ad set ID": names["ad_set_id"],
            "Ad name": names["ad"],
            "Ad ID": names["ad_id"],
            "Platform": [world.channels[i].placement for i in slots.channel[rows.slots]],
            "Age": [world.ages[i] for i in slots.age[rows.slots]],
            "Device platform": [DEVICE_LABELS[world.devices[i]] for i in slots.device[rows.slots]],
            "Region": [world.ad_sets[i].region for i in slots.ad_set[rows.slots]],
            "Amount spent (INR)": np.round(rows.take(sim.delivery.spend).astype(np.float64), 2),
            "Impressions": impressions,
            "Reach": reach.astype(np.int64),
            "Frequency": np.round(impressions / reach, 2),
            "Link clicks": rows.take(sim.delivery.clicks),
            "Purchases": rows.take(sim.paid.platform_conversions).astype(np.int64),
            "Purchases conversion value": np.round(
                rows.take(sim.paid.platform_revenue).astype(np.float64), 2
            ),
        },
        columns=COLUMNS,
    )
