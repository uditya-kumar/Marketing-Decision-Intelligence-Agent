"""Unit tests for application settings (pure, no I/O)."""

from __future__ import annotations

import pytest
from pydantic_settings import SettingsConfigDict

from mdia.core.errors import ConfigError
from mdia.core.settings import Settings, get_settings


@pytest.mark.unit
def test_missing_database_url_fails_fast_with_clear_message(
    monkeypatch: pytest.MonkeyPatch, tmp_path: object
) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    # Point at a non-existent env file so the real .env is not read.
    monkeypatch.setattr(
        Settings,
        "model_config",
        SettingsConfigDict(env_file=str(tmp_path) + "/none.env", extra="ignore"),
    )
    get_settings.cache_clear()
    try:
        with pytest.raises(ConfigError) as exc:
            get_settings()
        assert "DATABASE_URL" in str(exc.value)
    finally:
        get_settings.cache_clear()


@pytest.mark.unit
def test_sqlalchemy_url_uses_psycopg_driver() -> None:
    settings = Settings(_env_file=None, database_url="postgresql://u:p@h/db")  # type: ignore[call-arg]
    assert settings.sqlalchemy_url == "postgresql+psycopg://u:p@h/db"


@pytest.mark.unit
def test_sqlalchemy_url_leaves_explicit_driver_untouched() -> None:
    url = "postgresql+psycopg://u:p@h/db"
    settings = Settings(_env_file=None, database_url=url)  # type: ignore[call-arg]
    assert settings.sqlalchemy_url == url
