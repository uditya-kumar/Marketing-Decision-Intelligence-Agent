"""Integration fixtures: a migrated Neon ``test`` branch, emptied before each test."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from mdia.core.settings import get_settings
from mdia.db.base import Base
from mdia.db.session import get_session
from mdia.main import create_app

if TYPE_CHECKING:
    from collections.abc import Iterator

    from sqlalchemy import Engine

BACKEND_DIR = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="session")
def test_engine() -> Iterator[Engine]:
    url = get_settings().sqlalchemy_url_test
    if not url:
        pytest.skip("DATABASE_URL_TEST not configured")
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.attributes["sqlalchemy_url"] = url
    command.upgrade(config, "head")
    engine = create_engine(url, pool_pre_ping=True)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(test_engine: Engine) -> Iterator[Session]:
    tables = ", ".join(table.name for table in Base.metadata.sorted_tables)
    with test_engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
    with Session(test_engine, expire_on_commit=False) as session:
        yield session


@pytest.fixture
def client(db_session: Session) -> TestClient:
    app = create_app()

    def _session() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_session] = _session
    return TestClient(app)
