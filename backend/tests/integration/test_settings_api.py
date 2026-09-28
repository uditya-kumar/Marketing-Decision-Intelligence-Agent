"""Settings API against the Neon test branch (task 3.1)."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "csv"

pytestmark = pytest.mark.integration

VALID: dict[str, Any] = {
    "business_name": "NovaWear",
    "gross_margin_pct": 55,
    "target_cpa": 500,
    "target_roas": 3.5,
    "monthly_revenue_goal": 2_000_000,
    "monthly_budgets": {"google_ads": 520_000, "meta_ads": 760_000},
    "festive_windows": [{"name": "Navratri", "start": "2026-10-11", "end": "2026-10-20"}],
    "protected_campaign_ids": [],
}


def test_settings_are_unconfigured_until_saved(client: TestClient) -> None:
    body = client.get("/api/v1/settings").json()
    assert body == {
        "configured": False,
        "settings": None,
        "break_even_roas": None,
        "target_roas_profitable": None,
    }


def test_saved_settings_persist_and_derive_break_even_roas(client: TestClient) -> None:
    saved = client.put("/api/v1/settings", json=VALID)
    assert saved.status_code == 200, saved.text

    body = client.get("/api/v1/settings").json()
    assert body["configured"] is True
    assert body["settings"] == VALID
    assert body["break_even_roas"] == pytest.approx(100 / 55)
    assert body["target_roas_profitable"] is True


@pytest.mark.parametrize(
    "change",
    [
        {"gross_margin_pct": 0},
        {"gross_margin_pct": 120},
        {"target_cpa": -1},
        {"monthly_budgets": {"google_ads": -5}},
        {"monthly_budgets": {"tiktok": 100}},
        {"festive_windows": [{"name": "Diwali", "start": "2026-11-10", "end": "2026-11-01"}]},
        {"business_name": ""},
    ],
)
def test_invalid_settings_are_rejected(client: TestClient, change: dict[str, Any]) -> None:
    assert client.put("/api/v1/settings", json=VALID | change).status_code == 422
    assert client.get("/api/v1/settings").json()["configured"] is False


def test_protected_campaigns_must_exist(client: TestClient) -> None:
    unknown = client.put("/api/v1/settings", json=VALID | {"protected_campaign_ids": [999]})
    assert unknown.status_code == 422
    assert "999" in unknown.text

    upload = [("files", ("google.csv", (FIXTURES / "google_ads.csv").read_bytes(), "text/csv"))]
    client.post("/api/v1/ingestion/upload", files=upload)
    campaigns = client.get("/api/v1/settings/campaigns").json()
    assert [c["name"] for c in campaigns] == ["NW | Search | Brand"]

    ids = [campaigns[0]["id"]]
    saved = client.put("/api/v1/settings", json=VALID | {"protected_campaign_ids": ids})
    assert saved.status_code == 200
    assert saved.json()["settings"]["protected_campaign_ids"] == ids
