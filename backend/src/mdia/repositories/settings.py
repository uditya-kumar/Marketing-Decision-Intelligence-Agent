"""The single business-settings row."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from mdia.models import BusinessSettings

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

SETTINGS_ID = 1


class SettingsRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self) -> BusinessSettings | None:
        return self._session.get(BusinessSettings, SETTINGS_ID)

    def save(self, values: dict[str, Any]) -> BusinessSettings:
        settings = self.get() or BusinessSettings(id=SETTINGS_ID)
        for name, value in values.items():
            setattr(settings, name, value)
        self._session.add(settings)
        self._session.flush()
        return settings
