"""`store_orders.csv` — shaped like Shopify's daily "Sales over time" report.

As in Shopify, discounts and returns are reported as negative amounts.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

from novawear_sim.exporters.common import window_indices

if TYPE_CHECKING:
    from datetime import date

    from novawear_sim.engine import Simulation

COLUMNS = [
    "Day",
    "Orders",
    "Gross sales",
    "Discounts",
    "Returns",
    "Net sales",
    "Shipping",
    "Taxes",
    "Total sales",
    "New customers",
    "Returning customers",
]


def store_orders_frame(sim: Simulation, start: date, end: date) -> pd.DataFrame:
    days = window_indices(sim, start, end)
    s = sim.store
    return pd.DataFrame(
        {
            "Day": [sim.timeline.dates[i].isoformat() for i in days],
            "Orders": s.orders[days],
            "Gross sales": s.gross_sales[days],
            "Discounts": -s.discounts[days],
            "Returns": -s.returns[days],
            "Net sales": s.net_sales[days],
            "Shipping": s.shipping[days],
            "Taxes": s.taxes[days],
            "Total sales": s.total_sales[days],
            "New customers": s.new_customers[days],
            "Returning customers": s.returning_customers[days],
        },
        columns=COLUMNS,
    )
