"""`web_analytics.csv` — shaped like a GA4 exploration export (source / medium × device)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

from novawear_sim.exporters.common import window_indices

if TYPE_CHECKING:
    from datetime import date

    from novawear_sim.engine import Simulation

COLUMNS = [
    "Date",
    "Session source / medium",
    "Device category",
    "Sessions",
    "Engaged sessions",
    "Add to carts",
    "Checkouts",
    "Ecommerce purchases",
    "Purchase revenue",
]


def web_analytics_frame(sim: Simulation, start: date, end: date) -> pd.DataFrame:
    days = window_indices(sim, start, end)
    web = sim.web
    width = len(web.source_medium)
    d, c = (g.ravel() for g in np.meshgrid(days, np.arange(width), indexing="ij"))
    rec = web.recorded
    keep = rec.sessions[d, c] > 0
    d, c = d[keep], c[keep]
    return pd.DataFrame(
        {
            # GA4 exports dates as YYYYMMDD.
            "Date": [sim.timeline.dates[i].strftime("%Y%m%d") for i in d],
            "Session source / medium": [web.source_medium[i] for i in c],
            "Device category": [web.device[i] for i in c],
            "Sessions": rec.sessions[d, c],
            "Engaged sessions": rec.engaged[d, c],
            "Add to carts": rec.add_to_cart[d, c],
            "Checkouts": rec.checkout[d, c],
            "Ecommerce purchases": rec.purchases[d, c],
            "Purchase revenue": np.round(rec.revenue[d, c], 2),
        },
        columns=COLUMNS,
    )
