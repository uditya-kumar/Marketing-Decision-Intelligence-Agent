"""Application settings, loaded from environment / ``.env``.

Fails fast: if a required variable (e.g. ``DATABASE_URL``) is missing, importing the
settings raises :class:`ConfigError` with a message that names what to fix, instead
of surfacing a raw ``pydantic`` traceback deep inside a request.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic import ValidationError as PydanticValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

from mdia.core.errors import ConfigError


class Settings(BaseSettings):
    """Typed application configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- App ---
    app_env: Literal["dev", "test", "prod"] = "dev"
    log_level: str = "INFO"

    # --- Database (Neon Postgres) ---
    database_url: str = Field(..., description="Neon connection string for the active branch")
    database_url_test: str | None = Field(
        default=None, description="Neon 'test' branch URL; required for integration tests"
    )

    # --- LLM provider (used from Phase 8 onward; only factory.py reads these) ---
    llm_provider: str = "bedrock_converse"
    llm_model: str = ""
    llm_temperature: float = 0.0
    aws_region: str = "us-east-1"
    google_api_key: str = ""

    @property
    def sqlalchemy_url(self) -> str:
        """Return ``database_url`` normalised to the psycopg 3 driver."""
        return _with_psycopg_driver(self.database_url)

    @property
    def sqlalchemy_url_test(self) -> str | None:
        """Return the test-branch URL normalised to the psycopg 3 driver, if set."""
        return _with_psycopg_driver(self.database_url_test) if self.database_url_test else None


def _with_psycopg_driver(url: str) -> str:
    """Ensure the URL uses SQLAlchemy's ``postgresql+psycopg`` dialect."""
    if url.startswith("postgresql+psycopg://"):
        return url
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://") :]
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://") :]
    return url


@lru_cache
def get_settings() -> Settings:
    """Return cached settings, raising a clear :class:`ConfigError` if misconfigured."""
    try:
        return Settings()
    except PydanticValidationError as exc:
        missing = ", ".join(
            str(err["loc"][0]).upper() for err in exc.errors() if err["type"] == "missing"
        )
        detail = f"Missing required settings: {missing}. " if missing else ""
        raise ConfigError(
            f"{detail}Copy backend/.env.example to backend/.env and fill in the values."
        ) from exc
