"""Whatever fails, the body has the same three keys (task 11.1)."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

from mdia.api import errors
from mdia.core.errors import MdiaError, NotFoundError, ValidationError


class _Body(BaseModel):
    week_end: str


@pytest.fixture
def client() -> TestClient:
    app = FastAPI(responses=errors.RESPONSES)
    errors.register(app)

    @app.get("/missing")
    def _missing() -> None:
        raise NotFoundError("Opportunity 7 does not exist.")

    @app.get("/invalid")
    def _invalid() -> None:
        raise ValidationError("That week has no data yet.")

    @app.get("/broken")
    def _broken() -> None:
        raise MdiaError("the repository blew up with a connection string in the message")

    @app.get("/surprise")
    def _surprise() -> None:
        raise RuntimeError("secret internals")

    @app.post("/weekly")
    def _weekly(body: _Body) -> _Body:
        return body

    return TestClient(app, raise_server_exceptions=False)


def test_a_missing_thing_says_so_in_words_a_screen_can_show(client: TestClient) -> None:
    response = client.get("/missing")

    assert response.status_code == 404
    assert response.json() == {
        "code": "not_found",
        "message": "Opportunity 7 does not exist.",
        "fields": [],
    }


def test_a_domain_rule_is_reported_as_invalid_input(client: TestClient) -> None:
    response = client.get("/invalid")

    assert response.status_code == 422
    assert response.json()["code"] == "invalid_input"
    assert response.json()["message"] == "That week has no data yet."


def test_a_bad_payload_names_the_field_the_form_used(client: TestClient) -> None:
    response = client.post("/weekly", json={})

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "invalid_input"
    assert body["fields"] == [{"field": "week_end", "message": "Field required"}]


@pytest.mark.parametrize("path", ["/broken", "/surprise"])
def test_our_own_failures_never_leak_their_detail(client: TestClient, path: str) -> None:
    response = client.get(path)

    assert response.status_code == 500
    assert response.json() == {
        "code": "server_error",
        "message": errors.SERVER_MESSAGE,
        "fields": [],
    }
