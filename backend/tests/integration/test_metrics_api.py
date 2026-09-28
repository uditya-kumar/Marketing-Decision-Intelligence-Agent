"""Metrics and Today APIs checked against a hand calculation on the fixtures (task 3.5).

The fixtures cover 2026-04-18 and 2026-04-19. Summed by hand from the CSVs:

    Google  18th: spend  800.63, conversions 3.26, value  6,723.32
            19th: spend  855.63, conversions 5.63, value 11,408.74
    Meta    18th: spend  916.51, purchases   6,    value 11,734.72
            19th: spend 1147.66, purchases   1,    value  1,044.38
    Store net sales: 166,142.39 + 173,715.94 = 339,858.33

    spend 3,720.43 · conversions 15.89 · platform value 30,911.16
    ROAS = 30,911.16 / 3,720.43 = 8.3085     MER = 339,858.33 / 3,720.43 = 91.3492
    CPA  =  3,720.43 / 15.89    = 234.1366
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "csv"
SOURCE_FILES = ("google_ads.csv", "meta_ads.csv", "web_analytics.csv", "store_orders.csv")

pytestmark = pytest.mark.integration


@pytest.fixture
def loaded(client: TestClient) -> TestClient:
    files = [("files", (n, (FIXTURES / n).read_bytes(), "text/csv")) for n in SOURCE_FILES]
    assert client.post("/api/v1/ingestion/upload", files=files).status_code == 200
    return client


def test_today_is_empty_without_data(client: TestClient) -> None:
    body = client.get("/api/v1/today").json()
    assert {k: body[k] for k in ("as_of_date", "configured", "period", "kpis", "trend")} == {
        "as_of_date": None,
        "configured": False,
        "period": None,
        "kpis": [],
        "trend": [],
    }
    assert body["pacing"] == {"month": None, "total": None, "channels": []}
    assert all(s["status"] == "broken" for s in body["trust"]["sources"])


def test_today_matches_the_hand_calculation(loaded: TestClient) -> None:
    settings = {
        "business_name": "NovaWear",
        "gross_margin_pct": 55,
        "target_cpa": 250,
        "target_roas": 8,
        "monthly_revenue_goal": 1_500_000,
    }
    assert loaded.put("/api/v1/settings", json=settings).status_code == 200

    body = loaded.get("/api/v1/today").json()
    assert body["as_of_date"] == "2026-04-19"
    assert body["configured"] is True
    assert body["period"] == {"start": "2026-04-13", "end": "2026-04-19"}

    kpis = {k["metric"]: k for k in body["kpis"]}
    assert list(kpis) == ["store_revenue", "spend", "roas", "mer", "cpa"]
    assert kpis["store_revenue"]["value"] == pytest.approx(339_858.33)
    assert kpis["spend"]["value"] == pytest.approx(3_720.43)
    assert kpis["roas"]["value"] == pytest.approx(30_911.16 / 3_720.43)
    assert kpis["mer"]["value"] == pytest.approx(339_858.33 / 3_720.43)
    assert kpis["cpa"]["value"] == pytest.approx(3_720.43 / 15.89)
    # Nothing was loaded for the week before, so there's no delta to show.
    assert all(k["previous"] is None and k["change_pct"] is None for k in body["kpis"])

    # ROAS 8.31 is within 5 % of the 8.0 target; CPA 234 is > 5 % under the 250 limit.
    assert kpis["roas"]["goal"] == {"target": 8.0, "status": "on_track"}
    assert kpis["cpa"]["goal"] == {"target": 250.0, "status": "ahead"}
    # MER is judged against break-even (100 / 55 = 1.82×); revenue against 7/30 of the goal.
    assert kpis["mer"]["goal"] == {"target": pytest.approx(100 / 55), "status": "ahead"}
    assert kpis["store_revenue"]["goal"] == {"target": 350_000.0, "status": "on_track"}
    assert kpis["spend"]["goal"] is None
    assert kpis["spend"]["higher_is_better"] is None
    assert kpis["cpa"]["higher_is_better"] is False
    # Two days is too little history for a tracking check, so nothing is muted.
    assert all(k["reliable"] for k in body["kpis"])

    trend = body["trend"]
    assert len(trend) == 30
    assert trend[-1]["date"] == "2026-04-19"
    assert trend[-1]["spend"] == pytest.approx(855.63 + 1_147.66)
    assert trend[-1]["cpa"] == pytest.approx((855.63 + 1_147.66) / (5.63 + 1))
    assert trend[0]["spend"] is None


def test_metrics_by_channel_match_the_hand_calculation(loaded: TestClient) -> None:
    response = loaded.get("/api/v1/metrics", params={"metric": "cpa", "dimension": "channel"})
    body = response.json()
    assert response.status_code == 200, response.text
    assert body["period"] == {"start": "2026-03-21", "end": "2026-04-19"}

    series = {s["key"]: s for s in body["series"]}
    assert series.keys() == {"google_ads", "meta_ads"}
    google, meta = series["google_ads"], series["meta_ads"]
    assert google["value"] == pytest.approx((800.63 + 855.63) / (3.26 + 5.63))
    assert meta["value"] == pytest.approx((916.51 + 1_147.66) / 7)
    assert len(google["points"]) == 30
    assert google["points"][-1] == {"date": "2026-04-19", "value": pytest.approx(855.63 / 5.63)}
    assert google["points"][0]["value"] is None


def test_metrics_compare_with_the_previous_period(loaded: TestClient) -> None:
    params = {"metric": "spend", "days": 1, "end": "2026-04-19"}
    body = loaded.get("/api/v1/metrics", params=params).json()

    (total,) = body["series"]
    assert total["key"] == "total"
    assert total["value"] == pytest.approx(855.63 + 1_147.66)
    assert total["previous"] == pytest.approx(800.63 + 916.51)
    assert total["change_pct"] == pytest.approx((2_003.29 - 1_717.14) / 1_717.14 * 100)


def test_store_metrics_are_blank_when_sliced_by_channel(loaded: TestClient) -> None:
    params = {"metric": "mer", "dimension": "channel", "days": 2}
    body = loaded.get("/api/v1/metrics", params=params).json()
    assert all(s["value"] is None for s in body["series"])

    total = loaded.get("/api/v1/metrics", params={"metric": "mer", "days": 2}).json()
    assert total["series"][0]["value"] == pytest.approx(339_858.33 / 3_720.43)


def test_unknown_metric_is_rejected(client: TestClient) -> None:
    assert client.get("/api/v1/metrics", params={"metric": "vibes"}).status_code == 422
