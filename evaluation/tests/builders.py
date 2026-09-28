"""Small builders for the pieces a scorer reads, so a test can state only what it means."""

from __future__ import annotations

import datetime as dt

from mdia.agents.llm import CallRecord
from mdia.domain.opportunities import Opportunity
from mdia.domain.periods import Period
from mdia.domain.signals import Entity, Signal
from mdia.domain.trust import TrackingCheck, TrustStatus

from mdia_eval.replay import Run
from mdia_eval.truth import Event


def day(offset: int) -> dt.date:
    return dt.date(2026, 3, 1) + dt.timedelta(days=offset)


def signal(
    metric: str = "roas",
    *,
    channel: str | None = "meta_ads",
    detector: str = "baseline_change",
    as_of: dt.date | None = None,
) -> Signal:
    entity = Entity(level="campaign", key="c1", name="Campaign", channel=channel)  # type: ignore[arg-type]
    end = as_of or day(0)
    return Signal(
        id=f"sig-{metric}",
        detector=detector,  # type: ignore[arg-type]
        metric=metric,  # type: ignore[arg-type]
        entity=entity,
        window=Period(end - dt.timedelta(days=6), end),
        current=2.0,
        baseline=4.0,
        change_pct=-50.0,
        adverse=True,
    )


def opportunity(*signals: Signal, key: str = "campaign:c1", kind: str = "issue") -> Opportunity:
    chosen = signals or (signal(),)
    return Opportunity(
        key=key,
        kind=kind,  # type: ignore[arg-type]
        entity=chosen[0].entity,
        window=chosen[0].window,
        primary=chosen[0],
        signals=tuple(chosen),
        impact=10_000.0,
        score=10_000.0,
    )


def check(status: TrustStatus = "ok") -> TrackingCheck:
    return TrackingCheck(
        status=status,
        ratio_change=0.2 if status == "broken" else 1.0,
        since=None,
        conversions_change_pct=None,
        orders_change_pct=None,
    )


def run(
    as_of: dt.date,
    *,
    opportunities: tuple[Opportunity, ...] = (),
    tracking: dict[str, TrackingCheck] | None = None,
) -> Run:
    return Run(
        as_of=as_of,
        opportunities=list(opportunities),
        tracking=tracking or {"meta_ads": check()},  # type: ignore[arg-type]
    )


def event(
    kind: str = "tracking_break",
    *,
    start: dt.date | None = None,
    days: int = 5,
    entities: tuple[str, ...] = ("channel:meta_ads",),
    expected_action: str | None = None,
) -> Event:
    first = start or day(0)
    return Event(
        id=f"ev-{kind}",
        kind=kind,
        window=Period(first, first + dt.timedelta(days=days - 1)),
        onset="sudden",
        entities=frozenset(entities),
        metrics=frozenset({"roas"}),
        detectors=frozenset(),
        kind_expected="issue",
        expected_signal_type=None,
        expected_action=expected_action,
    )


def call(
    *,
    attempt: int = 1,
    grounded: bool = True,
    fallback: bool = False,
    purpose: str = "diagnosis",
    error: str | None = None,
) -> CallRecord:
    return CallRecord(
        purpose=purpose,
        provider="bedrock_converse",
        model="test",
        prompt_version="diagnosis-v1",
        attempt=attempt,
        latency_ms=10,
        grounded=grounded,
        fallback=fallback,
        error=error,
    )
