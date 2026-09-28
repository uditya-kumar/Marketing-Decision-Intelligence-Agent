"""Ingestion API against the Neon test branch (tasks 2.4 and 2.5)."""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import func, select

from mdia.models import FactAdDaily

if TYPE_CHECKING:
    from fastapi.testclient import TestClient
    from sqlalchemy.orm import Session

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "csv"
BACKFILL = Path(__file__).resolve().parents[3] / "generator" / "output" / "backfill"
SOURCE_FILES = ("google_ads.csv", "meta_ads.csv", "web_analytics.csv", "store_orders.csv")

pytestmark = pytest.mark.integration


def _upload(client: TestClient, files: list[tuple[str, bytes]]) -> dict:
    response = client.post(
        "/api/v1/ingestion/upload",
        files=[("files", (name, content, "text/csv")) for name, content in files],
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_upload_detects_every_source_and_computes_the_as_of_date(client: TestClient) -> None:
    files = [(name, (FIXTURES / name).read_bytes()) for name in SOURCE_FILES]
    body = _upload(client, [*files, ("notes.json", b'{"not": "a csv"}')])

    by_file = {run["file_name"]: run for run in body["runs"]}
    assert {by_file[name]["source"] for name in SOURCE_FILES} == {
        "google_ads",
        "meta_ads",
        "web_analytics",
        "store_orders",
    }
    assert all(by_file[name]["status"] == "success" for name in SOURCE_FILES)
    assert by_file["notes.json"]["status"] == "failed"
    assert by_file["notes.json"]["source"] is None
    assert body["status"]["as_of_date"] == "2026-04-19"
    assert body["status"]["missing_sources"] == []


def test_malformed_rows_are_reported_and_valid_rows_loaded(
    client: TestClient, db_session: Session
) -> None:
    header, *rows = (FIXTURES / "google_ads.csv").read_text(encoding="utf-8").splitlines()
    rows[1] = rows[1].replace(",INR,", ",USD,")
    rows[4] = ",".join(cell if i != 13 else "lots" for i, cell in enumerate(rows[4].split(",")))
    body = _upload(client, [("google.csv", "\n".join([header, *rows]).encode())])

    run = body["runs"][0]
    assert (run["status"], run["rows_accepted"], run["rows_rejected"]) == ("partial", 6, 2)
    assert [row["line"] for row in run["rejected_rows"]] == [3, 6]
    assert "Currency code" in run["rejected_rows"][0]["errors"][0]
    assert "Clicks" in run["rejected_rows"][1]["errors"][0]
    assert run["rejected_rows"][1]["values"]["Clicks"] == "lots"
    assert db_session.scalar(select(func.count()).select_from(FactAdDaily)) == 6
    assert body["status"]["missing_sources"] == ["meta_ads", "web_analytics", "store_orders"]
    assert body["status"]["as_of_date"] is None


def test_runs_are_listed_newest_first(client: TestClient) -> None:
    for name in ("store_orders.csv", "web_analytics.csv"):
        _upload(client, [(name, (FIXTURES / name).read_bytes())])

    runs = client.get("/api/v1/ingestion/runs").json()
    assert [run["file_name"] for run in runs] == ["web_analytics.csv", "store_orders.csv"]


def test_templates_describe_every_source(client: TestClient) -> None:
    templates = client.get("/api/v1/ingestion/templates").json()

    assert [t["source"] for t in templates] == [
        "google_ads",
        "meta_ads",
        "web_analytics",
        "store_orders",
    ]
    google = templates[0]
    assert google["csv_header"].startswith("Day,Campaign,Campaign ID")
    assert {"header": "Currency code", "type": "one of: INR", "stored": False} in google["columns"]


@pytest.mark.skipif(not BACKFILL.exists(), reason="run `novawear-sim backfill` first")
def test_180_day_backfill_loads_via_the_api(client: TestClient) -> None:
    files = [(name, (BACKFILL / name).read_bytes()) for name in SOURCE_FILES]
    body = _upload(client, files)

    expected_rows = {name: content.count(b"\n") - 1 for name, content in files}
    for run in body["runs"]:
        assert run["status"] == "success"
        assert run["rows_accepted"] == expected_rows[run["file_name"]]
    status = body["status"]
    assert status["as_of_date"] == "2026-10-14"
    assert all(source["days"] == 180 for source in status["sources"])
    assert {s["first_date"] for s in status["sources"]} == {str(dt.date(2026, 4, 18))}
