"""Tracking-break accuracy and suppression (FR-13.3).

Two questions, both answered from the replay: did the trust check notice the break the
generator injected, and while it was noticed, did the product stop giving performance
advice about that channel? The second is the one that matters — a break that is spotted
and still advised on is worse than one that is merely missed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from mdia.domain.scoring import is_suppressed

if TYPE_CHECKING:
    import datetime as dt
    from collections.abc import Iterator, Sequence

    from mdia.domain.sources import Channel

    from mdia_eval.replay import Run
    from mdia_eval.truth import Event

# §13: breaks caught, and advice suppressed, in at least nine cases out of ten.
TARGET_ACCURACY = 0.90
KIND = "tracking_break"


@dataclass(frozen=True, slots=True)
class Break:
    """One injected tracking break and what the replay did about it."""

    event_id: str
    channel: Channel | None
    # First day the check called the channel broken inside the window.
    caught_on: dt.date | None
    # Days it was called broken, out of the days the replay covered the window.
    caught_days: int
    window_days: int
    # Days from the break starting to the check calling it; the check needs a few days
    # of divergence before it can tell a break from a quiet week.
    lag_days: int | None
    # Opportunities shown on a known-broken day that rest on platform conversions.
    leaked: tuple[str, ...] = ()

    @property
    def caught(self) -> bool:
        return self.caught_on is not None

    @property
    def suppressed(self) -> bool:
        """Caught, and no platform-based advice about the channel escaped while it held."""
        return self.caught and not self.leaked


@dataclass(frozen=True, slots=True)
class TrustScore:
    """FR-13.3 over one replay."""

    breaks: list[Break] = field(default_factory=list)
    # Breaks that ended before the replay's first window: the check never saw a day of
    # them, so they are reported apart rather than counted as missed.
    uncovered: list[Break] = field(default_factory=list)
    # Channel-days called broken with no injected break running: the false alarms.
    false_days: int = 0
    # Channel-days the replay judged at all, as the denominator for those alarms.
    judged_days: int = 0

    @property
    def accuracy(self) -> float:
        """Share of injected breaks the check noticed."""
        return _ratio(sum(b.caught for b in self.breaks), len(self.breaks))

    @property
    def suppression(self) -> float:
        """Share of injected breaks where advice was held back as well as noticed."""
        return _ratio(sum(b.suppressed for b in self.breaks), len(self.breaks))

    @property
    def false_alarm_rate(self) -> float:
        return _ratio(self.false_days, self.judged_days)

    @property
    def missed(self) -> list[Break]:
        return [b for b in self.breaks if not b.caught]

    @property
    def leaked(self) -> list[Break]:
        return [b for b in self.breaks if b.caught and b.leaked]


def score(runs: Sequence[Run], events: Sequence[Event]) -> TrustScore:
    """Score every injected tracking break, and count broken days no break explains."""
    injected = [event for event in events if event.kind == KIND]
    windows = [event.window for event in injected]
    false_days = sum(
        len(run.broken)
        for run in runs
        if not any(window.start <= run.as_of <= window.end for window in windows)
    )
    found = [_break(event, runs) for event in injected]
    return TrustScore(
        breaks=[item for item in found if item.window_days],
        uncovered=[item for item in found if not item.window_days],
        false_days=false_days,
        judged_days=sum(len(run.tracking) for run in runs),
    )


def _break(event: Event, runs: Sequence[Run]) -> Break:
    channel = _channel(event)
    inside = [run for run in runs if event.window.start <= run.as_of <= event.window.end]
    caught = [run for run in inside if _called_broken(run, channel)]
    first = caught[0].as_of if caught else None
    return Break(
        event_id=event.id,
        channel=channel,
        caught_on=first,
        caught_days=len(caught),
        window_days=len(inside),
        lag_days=None if first is None else (first - event.window.start).days,
        leaked=tuple(sorted({key for run in caught for key in _leaks(run, channel)})),
    )


def _called_broken(run: Run, channel: Channel | None) -> bool:
    return bool(run.broken) if channel is None else channel in run.broken


def _leaks(run: Run, channel: Channel | None) -> Iterator[str]:
    """Opportunities the product should have held back on this day, but showed.

    The rule is the product's own (FR-7.2, ``scoring.is_suppressed``): a finding built on
    what the platform reported is meaningless while the pixel is broken, and a blended
    finding is tainted by any break at all. Anything counted by the store stays valid.
    """
    broken = run.broken if channel is None else (channel,)
    for opportunity in run.opportunities:
        if any(is_suppressed(signal, broken=broken) for signal in opportunity.signals):
            yield opportunity.key


def _channel(event: Event) -> Channel | None:
    """The export channel a break was injected on, if it names one."""
    for entity in sorted(event.entities):
        level, _, key = entity.partition(":")
        if level == "channel":
            return key  # type: ignore[return-value]
    return None


def _ratio(part: int, whole: int) -> float:
    return 0.0 if whole == 0 else part / whole
