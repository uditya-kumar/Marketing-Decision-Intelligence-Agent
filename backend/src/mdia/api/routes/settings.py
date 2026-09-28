"""Business settings routes: goals, economics, budgets and guardrails (FR-1)."""

from __future__ import annotations

from fastapi import APIRouter

from mdia.api.deps import SettingsServiceDep  # noqa: TC001 - FastAPI resolves it at runtime
from mdia.schemas.settings import CampaignOut, SettingsIn, SettingsOut

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=SettingsOut)
def get_settings(service: SettingsServiceDep) -> SettingsOut:
    """The saved settings, or ``configured: false`` before the first save."""
    return SettingsOut.model_validate(service.view())


@router.put("", response_model=SettingsOut)
def put_settings(values: SettingsIn, service: SettingsServiceDep) -> SettingsOut:
    """Replace the settings; invalid values are rejected with a 422."""
    return SettingsOut.model_validate(service.update(values))


@router.get("/campaigns", response_model=list[CampaignOut])
def campaigns(service: SettingsServiceDep) -> list[CampaignOut]:
    """Campaigns seen in uploaded data, for choosing which ones are protected."""
    return [CampaignOut.model_validate(c) for c in service.campaigns()]
