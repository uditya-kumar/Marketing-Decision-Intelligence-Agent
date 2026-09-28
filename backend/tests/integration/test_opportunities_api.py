"""The opportunities API (task 7.1) over a stored, rule-diagnosed opportunity.

The row is written through the same path the analysis run uses, so what the detail
endpoint returns is exactly what a real run would have made available.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from mdia.agents.investigation import build_investigation, investigate
from mdia.repositories.analysis import AnalysisRepository
from mdia.services.opportunity_rows import opportunity_row
from tests.builders import AS_OF, creative_fatigue

if TYPE_CHECKING:
    from fastapi.testclient import TestClient
    from sqlalchemy.orm import Session

pytestmark = pytest.mark.integration


@pytest.fixture
def stored(db_session: Session) -> dict[str, Any]:
    """One creative-fatigue opportunity, diagnosed by the rules (no LLM call)."""
    opportunity = creative_fatigue()
    result = investigate(build_investigation(None), opportunity)
    repository = AnalysisRepository(db_session)
    run = repository.start(AS_OF)
    repository.save(run.id, [opportunity_row(run.id, opportunity, None, result)])
    db_session.commit()
    return {"key": opportunity.key}


def test_the_list_ranks_open_opportunities_and_filters_by_status(
    client: TestClient, stored: dict[str, Any]
) -> None:
    body = client.get("/api/v1/opportunities").json()

    (row,) = body["opportunities"]
    assert row["key"] == stored["key"]
    assert row["status"] == "open"
    assert row["title"] == "Reel | Get Ready With Me costs more per sale"
    assert row["kind"] == "issue"
    assert row["channel_id"] == "meta_ads"
    assert row["band"] in {"high", "medium", "low"}
    assert row["impact"] > 0
    assert 0 < row["confidence"] <= 1
    assert row["cause_label"] == "Creative fatigue"
    assert row["signal_count"] >= 1

    assert client.get("/api/v1/opportunities", params={"status": "dismissed"}).json() == {
        "opportunities": []
    }
    assert client.get("/api/v1/opportunities", params={"kind": "win"}).json() == {
        "opportunities": []
    }


def test_the_detail_returns_the_four_sections(client: TestClient, stored: dict[str, Any]) -> None:
    body = client.get("/api/v1/opportunities/1").json()

    # What happened.
    assert "CPA" in body["summary"]["observation"]
    # Why: the evidence tree, decomposed.
    assert body["tree"]["metric"] == "cpa"
    assert [child["metric"] for child in body["tree"]["children"]] == ["cpc", "cvr"]
    # Likely cause, with the fallback marked as such.
    assert body["hypotheses"][0]["cause"] == "creative_fatigue"
    assert body["hypotheses"][0]["cause_label"] == "Creative fatigue"
    assert body["hypotheses"][0]["signal_ids"]
    assert body["alternatives"]
    assert body["grounded"] is False
    assert body["summary"]["diagnosis_source"] == "rules"
    # Recommended.
    assert body["recommendation"]["action"] == "rotate_creative"
    assert body["recommendation"]["expected_impact"][0] > 0
    assert "CPA" in body["recommendation"]["stop_condition"]
    assert body["signals"][0]["metric"] == "cpa"


def test_dismissing_records_the_reason(client: TestClient, stored: dict[str, Any]) -> None:
    body = client.post(
        "/api/v1/opportunities/1/dismiss", json={"reason": "Creative is retiring anyway."}
    ).json()

    assert body["status"] == "dismissed"
    assert body["dismissed_reason"] == "Creative is retiring anyway."
    assert client.get("/api/v1/opportunities", params={"status": "dismissed"}).json()[
        "opportunities"
    ]
    assert client.post("/api/v1/opportunities/1/dismiss", json={"reason": ""}).status_code == 422
    assert client.get("/api/v1/opportunities/404").status_code == 404
