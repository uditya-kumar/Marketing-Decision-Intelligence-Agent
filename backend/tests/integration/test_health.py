"""Integration test: /health reports the database as reachable on the dev branch."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from mdia.main import create_app


@pytest.mark.integration
def test_health_reports_database_ok() -> None:
    client = TestClient(create_app())
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["database"] == "ok"
    assert body["status"] == "ok"
    assert body["llm_provider"]
