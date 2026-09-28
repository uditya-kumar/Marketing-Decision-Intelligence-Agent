"""`google_ads.csv` — shaped like a Google Ads ad report with age / device / region segments.

Search campaigns report no reach, and conversions are fractional (data-driven attribution).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

from novawear_sim.exporters.common import ad_rows, entity_columns, row_dates

if TYPE_CHECKING:
    from datetime import date

    from novawear_sim.engine import Simulation

SOURCE = "google_ads"
DEVICE_LABELS = {"mobile": "Mobile phones", "desktop": "Computers"}
COLUMNS = [
    "Day",
    "Campaign",
    "Campaign ID",
    "Ad group",
    "Ad group ID",
    "Ad ID",
    "Ad name",
    "Age",
    "Device",
    "Region",
    "Currency code",
    "Cost",
    "Impr.",
    "Clicks",
    "Conversions",
    "Conv. value",
]


def google_ads_frame(sim: Simulation, start: date, end: date) -> pd.DataFrame:
    rows = ad_rows(sim, SOURCE, start, end)
    world, slots = sim.world, sim.world.slots
    names = entity_columns(sim, rows, SOURCE)
    frame = pd.DataFrame(
        {
            "Day": [d.isoformat() for d in row_dates(sim, rows)],
            "Campaign": names["campaign"],
            "Campaign ID": names["campaign_id"],
            "Ad group": names["ad_set"],
            "Ad group ID": names["ad_set_id"],
            "Ad ID": names["ad_id"],
            "Ad name": names["ad"],
            "Age": [world.ages[i] for i in slots.age[rows.slots]],
            "Device": [DEVICE_LABELS[world.devices[i]] for i in slots.device[rows.slots]],
            "Region": [world.ad_sets[i].region for i in slots.ad_set[rows.slots]],
            "Currency code": world.config.brand.currency,
            "Cost": np.round(rows.take(sim.delivery.spend).astype(np.float64), 2),
            "Impr.": rows.take(sim.delivery.impressions),
            "Clicks": rows.take(sim.delivery.clicks),
            "Conversions": np.round(rows.take(sim.paid.platform_conversions).astype(np.float64), 2),
            "Conv. value": np.round(rows.take(sim.paid.platform_revenue).astype(np.float64), 2),
        },
        columns=COLUMNS,
    )
    return frame
