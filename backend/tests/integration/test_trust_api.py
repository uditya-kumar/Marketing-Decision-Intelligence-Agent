"""Trust and pacing APIs on the two-day fixtures (task 4.3).

Month-to-date spend through 2026-04-19, summed by hand from the CSVs:
    Google 800.63 + 855.63 = 1,656.26      Meta 916.51 + 1,147.66 = 2,064.17
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "csv"

pytestmark = pytest.mark.integration


def _upload(client: TestClient, *names: str) -> None:
    files = [("files", (n, (FIXTURES / n).read_bytes(), "text/csv")) for n in names]
    assert client.post("/api/v1/ingestion/upload", files=files).status_code == 200


def test_trust_flags_sources_with_no_data(client: TestClient) -> None:
    _upload(client, "google_ads.csv", "store_orders.csv")

    body = client.get("/api/v1/trust").json()
    assert body["as_of_date"] is None

    sources = {s["source"]: s for s in body["sources"]}
    assert list(sources) == ["google_ads", "meta_ads", "web_analytics", "store_orders"]
    assert sources["google_ads"]["status"] == "ok"
    assert sources["google_ads"]["label"] == "Google Ads"
    assert sources["google_ads"]["freshness"] == {
        "last_date": "2026-04-19",
        "days_behind": 0,
        "missing_dates": [],
    }
    assert sources["meta_ads"]["status"] == "broken"
    assert sources["meta_ads"]["freshness"]["last_date"] is None
    # Without an as-of date there's nothing to compare conversions against.
    assert all(s["tracking"] is None for s in body["sources"])


def test_trust_is_ok_once_every_source_is_loaded(client: TestClient) -> None:
    _upload(client, "google_ads.csv", "meta_ads.csv", "web_analytics.csv", "store_orders.csv")

    body = client.get("/api/v1/trust").json()
    assert body["as_of_date"] == "2026-04-19"
    assert [s["status"] for s in body["sources"]] == ["ok"] * 4
    # Two days is too little history for a tracking check.
    assert all(s["tracking"] is None for s in body["sources"])


def test_today_paces_each_budgeted_channel(client: TestClient) -> None:
    _upload(client, "google_ads.csv", "meta_ads.csv", "web_analytics.csv", "store_orders.csv")
    settings = {
        "business_name": "NovaWear",
        "gross_margin_pct": 55,
        "monthly_budgets": {"google_ads": 2_600, "meta_ads": 2_000},
    }
    assert client.put("/api/v1/settings", json=settings).status_code == 200

    pacing = client.get("/api/v1/today").json()["pacing"]
    assert pacing["month"] == {"start": "2026-04-01", "end": "2026-04-19"}

    channels = {c["channel"]: c for c in pacing["channels"]}
    google, meta = channels["google_ads"]["pacing"], channels["meta_ads"]["pacing"]
    assert channels["meta_ads"]["label"] == "Meta Ads"
    # Google: 1,656.26 over 19 days projects to 2,615.15 of 2,600, which is on plan.
    assert google["spent"] == pytest.approx(1_656.26)
    assert google["projected"] == pytest.approx(1_656.26 / 19 * 30)
    assert google["status"] == "on_track"
    # Meta has already spent more than its whole month's budget.
    assert meta["spent_pct"] == pytest.approx(2_064.17 / 2_000 * 100)
    assert meta["status"] == "over"
    assert meta["suggested_daily"] == 0
    assert meta["remaining_budget"] == pytest.approx(2_000 - 2_064.17)
    assert pacing["total"]["budget"] == 4_600
    assert pacing["total"]["spent"] == pytest.approx(3_720.43)
    assert pacing["total"]["month_elapsed_pct"] == pytest.approx(19 / 30 * 100)
