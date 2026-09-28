"""Experiments and the decision log (tasks 8.1, 8.3) over a stored opportunity.

The row is written through the same path the analysis run uses, so the draft the API
fills in is the one a real run would have offered. The verdict is driven by inserting
the week of facts the next upload would bring, then asking the service to judge what
is due — which is exactly what ``AnalysisService.run`` does after it stores.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal
from typing import TYPE_CHECKING

import pytest

from mdia.agents.investigation import build_investigation, investigate
from mdia.models import DimAdSet, DimCampaign, DimChannel, DimCreative, FactAdDaily
from mdia.repositories.analysis import AnalysisRepository
from mdia.services.experiments import ExperimentService
from mdia.services.opportunity_rows import opportunity_row
from tests.builders import AS_OF, creative_fatigue

if TYPE_CHECKING:
    from fastapi.testclient import TestClient
    from sqlalchemy.orm import Session

pytestmark = pytest.mark.integration

# The creative the builders' fatigue scenario is about.
CREATIVE_ID = 42
AD_SET_ID = 31
CAMPAIGN_ID = 7
# Approval happens on the last day of data, so the test runs over the week after it.
JUDGED_ON = AS_OF + dt.timedelta(days=7)


@pytest.fixture
def run_id(db_session: Session) -> int:
    """One creative-fatigue opportunity, diagnosed by the rules (no LLM call)."""
    opportunity = creative_fatigue()
    result = investigate(build_investigation(None), opportunity)
    repository = AnalysisRepository(db_session)
    run = repository.start(AS_OF)
    repository.save(run.id, [opportunity_row(run.id, opportunity, None, result)])
    db_session.commit()
    return run.id


def test_a_draft_is_filled_in_from_the_recommendation(client: TestClient, run_id: int) -> None:
    body = client.post("/api/v1/experiments", json={"opportunity_id": 1}).json()

    assert body["status"] == "draft"
    assert body["action"] == "rotate_creative"
    assert body["metric"] == "cpa"
    assert body["duration_days"] == 7
    assert body["baseline"] > body["target"] > 0
    assert "should move CPA" in body["hypothesis"]
    assert body["opportunity"]["id"] == 1
    # Asking twice does not open a second change on the same opportunity.
    assert client.post("/api/v1/experiments", json={"opportunity_id": 1}).json()["id"] == body["id"]


def test_approving_starts_the_clock_and_logs_the_decision(client: TestClient, run_id: int) -> None:
    client.post("/api/v1/experiments", json={"opportunity_id": 1})

    body = client.post("/api/v1/experiments/1/approve", json={"reason": None}).json()

    assert body["status"] == "running"
    assert body["started_on"] == AS_OF.isoformat()
    assert body["ends_on"] == JUDGED_ON.isoformat()
    assert body["progress"] == {"day": 0, "total": 7, "due": False}
    assert body["opportunity"]["status"] == "experimenting"
    # A decision already made cannot be made again.
    assert client.post("/api/v1/experiments/1/approve", json={"reason": None}).status_code == 422

    (entry,) = client.get("/api/v1/decisions").json()["decisions"]
    assert entry["kind"] == "approve"
    assert entry["experiment"]["id"] == 1
    assert entry["opportunity"]["id"] == 1


def test_rejecting_logs_the_reason_and_leaves_the_opportunity_open(
    client: TestClient, run_id: int
) -> None:
    client.post("/api/v1/experiments", json={"opportunity_id": 1})

    body = client.post(
        "/api/v1/experiments/1/reject", json={"reason": "The creative is retiring anyway."}
    ).json()

    assert body["status"] == "rejected"
    assert body["reason"] == "The creative is retiring anyway."
    assert body["opportunity"]["status"] == "open"

    (entry,) = client.get("/api/v1/decisions").json()["decisions"]
    assert entry["kind"] == "reject"
    assert entry["reason"] == "The creative is retiring anyway."


def test_dismissing_an_opportunity_also_reaches_the_log(client: TestClient, run_id: int) -> None:
    client.post("/api/v1/opportunities/1/dismiss", json={"reason": "Seasonal, not a problem."})

    (entry,) = client.get("/api/v1/decisions").json()["decisions"]
    assert entry["kind"] == "dismiss"
    assert entry["experiment"] is None
    assert entry["impact"] > 0


def test_the_next_week_of_data_completes_a_running_experiment(
    client: TestClient, db_session: Session, run_id: int
) -> None:
    client.post("/api/v1/experiments", json={"opportunity_id": 1})
    client.post("/api/v1/experiments/1/approve", json={"reason": None})
    _facts(db_session, cpa_before=610.0, cpa_after=420.0)

    judged = ExperimentService(db_session).evaluate_due(JUDGED_ON, run_id)
    db_session.commit()

    assert judged == [1]
    (body,) = client.get("/api/v1/experiments").json()["experiments"]
    assert body["status"] == "completed"
    assert body["verdict"] == "worked"
    assert body["before"] == pytest.approx(610.0)
    assert body["after"] == pytest.approx(420.0)
    assert body["sample_days"] == 7
    # A change that worked closes the problem it was raised for.
    assert body["opportunity"]["status"] == "resolved"


def _facts(session: Session, *, cpa_before: float, cpa_after: float) -> None:
    """A week of delivery either side of the approval, at the two CPAs given."""
    # One level at a time: each row's parent has to exist before it is inserted.
    for row in (
        DimChannel(id="meta_ads", name="Meta Ads"),
        DimCampaign(id=CAMPAIGN_ID, channel_id="meta_ads", external_id="c7", name="Reels"),
        DimAdSet(id=AD_SET_ID, campaign_id=CAMPAIGN_ID, external_id="a31", name="Broad"),
        DimCreative(id=CREATIVE_ID, ad_set_id=AD_SET_ID, external_id="cr42", name="Reel"),
    ):
        session.add(row)
        session.flush()
    for offset in range(-6, 8):
        day = AS_OF + dt.timedelta(days=offset)
        cpa = cpa_before if day <= AS_OF else cpa_after
        session.add(
            FactAdDaily(
                date=day,
                creative_id=CREATIVE_ID,
                age_group="25-34",
                device="mobile",
                region="Maharashtra",
                channel_id="meta_ads",
                campaign_id=CAMPAIGN_ID,
                ad_set_id=AD_SET_ID,
                impressions=100_000,
                reach=60_000,
                clicks=1_500,
                spend=Decimal(str(cpa * 10)),
                platform_conversions=Decimal(10),
                platform_revenue=Decimal(50_000),
            )
        )
    session.commit()
