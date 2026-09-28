"""Integration test: the Neon 'test' branch is reachable.

Requires ``DATABASE_URL_TEST`` (the Neon test branch). Skipped if it is not set.
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine, text

from mdia.core.settings import get_settings


@pytest.mark.integration
def test_test_branch_answers_select_one() -> None:
    url = get_settings().sqlalchemy_url_test
    if not url:
        pytest.skip("DATABASE_URL_TEST not configured")

    engine = create_engine(url, pool_pre_ping=True)
    try:
        with engine.connect() as conn:
            assert conn.execute(text("SELECT 1")).scalar_one() == 1
    finally:
        engine.dispose()
