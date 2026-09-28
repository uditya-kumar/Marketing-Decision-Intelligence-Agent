"""The weekly report over the CSV fixtures (task 9.3): generated, stored, listed.

The model is switched off here, so the report is the template one: this test is about
the week reaching the database and coming back, not about the wording.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "csv"
SOURCE_FILES = ("google_ads.csv", "meta_ads.csv", "web_analytics.csv", "store_orders.csv")
# The last day the fixtures cover, which is the week a fresh report ends on.
AS_OF = "2026-04-19"

pytestmark = pytest.mark.integration


@pytest.fixture
def loaded(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr("mdia.services.reports.get_chat_model", lambda: None)
    files = [("files", (n, (FIXTURES / n).read_bytes(), "text/csv")) for n in SOURCE_FILES]
    assert client.post("/api/v1/ingestion/upload", files=files).status_code == 200
    return client


def test_there_is_nothing_to_report_before_any_data(client: TestClient) -> None:
    assert client.post("/api/v1/reports/weekly", json={}).status_code == 422
    assert client.get("/api/v1/reports").json() == {"reports": [], "next_week_end": None}


def test_a_report_covers_the_week_to_the_last_day_of_data(loaded: TestClient) -> None:
    response = loaded.post("/api/v1/reports/weekly", json={})

    assert response.status_code == 201
    body = response.json()
    assert body["week"]["end"] == AS_OF
    assert body["source"] == "template"
    assert body["grounded"] is False
    assert body["summary"][0].startswith("Revenue was ")
    assert any(line.startswith("This week's KPIs.") for line in body["detail"])


def test_past_reports_are_listed_newest_first(loaded: TestClient) -> None:
    loaded.post("/api/v1/reports/weekly", json={"week_end": "2026-04-18"})
    loaded.post("/api/v1/reports/weekly", json={})

    body = loaded.get("/api/v1/reports").json()

    assert [report["week"]["end"] for report in body["reports"]] == [AS_OF, "2026-04-18"]
    assert body["next_week_end"] == AS_OF


def test_generating_the_same_week_again_replaces_it(loaded: TestClient) -> None:
    first = loaded.post("/api/v1/reports/weekly", json={}).json()
    again = loaded.post("/api/v1/reports/weekly", json={}).json()

    assert again["id"] == first["id"]
    assert len(loaded.get("/api/v1/reports").json()["reports"]) == 1


def test_one_report_is_read_back_by_id(loaded: TestClient) -> None:
    created = loaded.post("/api/v1/reports/weekly", json={}).json()

    read = loaded.get(f"/api/v1/reports/{created['id']}").json()

    assert read == created
    assert loaded.get("/api/v1/reports/404").status_code == 404
