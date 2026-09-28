"""API DTOs for the health endpoint."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Reports overall status plus database and configured LLM provider."""

    status: Literal["ok", "degraded"]
    database: Literal["ok", "unavailable"]
    llm_provider: str
