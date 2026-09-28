"""Business settings use case (FR-1): read, save and derive break-even ROAS."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from mdia.core.errors import ValidationError
from mdia.domain.goals import break_even_roas, is_profitable_roas
from mdia.repositories.entities import EntityRepository
from mdia.repositories.settings import SettingsRepository

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sqlalchemy.orm import Session

    from mdia.models import BusinessSettings, DimCampaign
    from mdia.schemas.settings import SettingsIn


@dataclass(frozen=True, slots=True)
class SettingsView:
    configured: bool
    settings: BusinessSettings | None
    break_even_roas: float | None
    target_roas_profitable: bool | None


class SettingsService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._settings = SettingsRepository(session)
        self._entities = EntityRepository(session)

    def current(self) -> BusinessSettings | None:
        return self._settings.get()

    def view(self) -> SettingsView:
        return _view(self._settings.get())

    def update(self, values: SettingsIn) -> SettingsView:
        known = {campaign.id for campaign in self._entities.list_campaigns()}
        if unknown := sorted(set(values.protected_campaign_ids) - known):
            raise ValidationError(f"Unknown campaign IDs: {', '.join(map(str, unknown))}.")
        saved = self._settings.save(values.model_dump(mode="json"))
        self._session.commit()
        return _view(saved)

    def campaigns(self) -> Sequence[DimCampaign]:
        return self._entities.list_campaigns()


def _view(settings: BusinessSettings | None) -> SettingsView:
    if settings is None:
        return SettingsView(False, None, None, None)
    margin = float(settings.gross_margin_pct)
    target = settings.target_roas
    profitable = None if target is None else is_profitable_roas(float(target), margin)
    return SettingsView(True, settings, break_even_roas(margin), profitable)
