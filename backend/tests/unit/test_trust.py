"""Data trust: as-of date and missing sources."""

from __future__ import annotations

import datetime as dt

import pytest

from mdia.domain.trust import as_of_date, missing_sources

pytestmark = pytest.mark.unit

D = dt.date


def test_as_of_is_the_earliest_latest_date_across_sources() -> None:
    latest = {
        "google_ads": D(2026, 10, 14),
        "meta_ads": D(2026, 10, 14),
        "web_analytics": D(2026, 10, 13),
        "store_orders": D(2026, 10, 14),
    }

    assert as_of_date(latest) == D(2026, 10, 13)
    assert missing_sources(latest) == []


def test_as_of_is_unknown_until_every_source_has_data() -> None:
    latest = {"google_ads": D(2026, 10, 14), "store_orders": None}

    assert as_of_date(latest) is None
    assert missing_sources(latest) == ["meta_ads", "web_analytics", "store_orders"]
