from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

import numpy as np
import pytest

from novawear_sim.errors import GeneratorError
from novawear_sim.exporters import google_ads, meta_ads, store, web
from novawear_sim.exporters.google_ads import google_ads_frame
from novawear_sim.exporters.meta_ads import meta_ads_frame
from novawear_sim.exporters.store import store_orders_frame
from novawear_sim.exporters.web import web_analytics_frame

if TYPE_CHECKING:
    from novawear_sim.engine import Simulation

START, END = date(2026, 3, 1), date(2026, 3, 7)


def test_google_ads_export_looks_like_a_google_ads_report(baseline: Simulation) -> None:
    df = google_ads_frame(baseline, START, END)
    assert list(df.columns) == google_ads.COLUMNS
    assert {"Cost", "Impr.", "Clicks", "Conversions", "Conv. value"} <= set(df.columns)
    assert set(df["Device"]) == {"Mobile phones", "Computers"}
    assert df["Campaign ID"].str.fullmatch(r"\d{11,12}").all()
    assert (df["Impr."] > 0).all()
    # Data-driven attribution gives fractional conversions.
    assert (df["Conversions"] % 1 != 0).any()


def test_meta_ads_export_looks_like_ads_manager(baseline: Simulation) -> None:
    df = meta_ads_frame(baseline, START, END)
    assert list(df.columns) == meta_ads.COLUMNS
    assert set(df["Platform"]) == {"facebook", "instagram"}
    assert df["Ad ID"].str.fullmatch(r"120\d{15}").all()
    assert (df["Reach"] <= df["Impressions"]).all()
    assert (df["Reporting starts"] == df["Reporting ends"]).all()
    assert np.allclose(df["Frequency"], df["Impressions"] / df["Reach"], atol=0.01)


def test_web_export_looks_like_ga4(baseline: Simulation) -> None:
    df = web_analytics_frame(baseline, START, END)
    assert list(df.columns) == web.COLUMNS
    assert df["Date"].str.fullmatch(r"\d{8}").all()
    assert {"google / cpc", "facebook / paid_social", "(direct) / (none)"} <= set(
        df["Session source / medium"]
    )
    assert (df["Engaged sessions"] <= df["Sessions"]).all()


def test_store_export_looks_like_shopify(baseline: Simulation) -> None:
    df = store_orders_frame(baseline, START, END)
    assert list(df.columns) == store.COLUMNS
    assert len(df) == 7
    assert (df["Discounts"] <= 0).all() and (df["Returns"] <= 0).all()
    assert np.allclose(
        df["Net sales"], df["Gross sales"] + df["Discounts"] + df["Returns"], atol=0.02
    )


def test_exports_are_restricted_to_the_window(baseline: Simulation) -> None:
    days = google_ads_frame(baseline, START, END)["Day"]
    assert days.min() == "2026-03-01" and days.max() == "2026-03-07"


def test_window_outside_simulation_is_rejected(baseline: Simulation) -> None:
    with pytest.raises(GeneratorError, match="outside the simulated range"):
        store_orders_frame(baseline, date(2026, 3, 30), date(2026, 4, 5))
