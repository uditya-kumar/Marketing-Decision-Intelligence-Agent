"""The Today screen: KPIs, data trust and pacing, sharing one read of coverage and settings."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from mdia.domain.trust import unreliable_metrics
from mdia.repositories.facts import FactRepository
from mdia.repositories.settings import SettingsRepository
from mdia.services.metrics import MetricsService
from mdia.services.pacing import PacingService
from mdia.services.trust import TrustService

if TYPE_CHECKING:
    import datetime as dt

    from sqlalchemy.orm import Session

    from mdia.domain.periods import Period
    from mdia.services.metrics import KpiSummary, TrendPoint
    from mdia.services.pacing import PacingView
    from mdia.services.trust import TrustView


@dataclass(frozen=True, slots=True)
class TodayView:
    as_of_date: dt.date | None
    configured: bool
    period: Period | None
    kpis: list[KpiSummary]
    trend: list[TrendPoint]
    trust: TrustView
    pacing: PacingView


class TodayService:
    def __init__(self, session: Session) -> None:
        self._facts = FactRepository(session)
        self._settings = SettingsRepository(session)
        self._metrics = MetricsService(session)
        self._trust = TrustService(session)
        self._pacing = PacingService(session)

    def today(self) -> TodayView:
        settings = self._settings.get()
        trust = self._trust.check(self._facts.coverage())
        as_of = trust.as_of_date
        budgets = settings.monthly_budgets if settings else {}
        pacing = self._pacing.month(as_of, budgets or {})
        if as_of is None:
            return TodayView(None, settings is not None, None, [], [], trust, pacing)
        kpis = self._metrics.today(as_of, settings, unreliable_metrics(trust.sources))
        return TodayView(
            as_of, settings is not None, kpis.period, kpis.kpis, kpis.trend, trust, pacing
        )
