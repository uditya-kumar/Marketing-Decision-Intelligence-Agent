"""Detection accuracy (FR-13.1): precision, recall, F1, days-to-detect, false alarms.

A replay raises the same opportunity on many consecutive days, which a marketer would
experience as one alert. Scoring therefore works on *episodes* — a run of days on which
one opportunity key was open — so a long-lived finding counts once, the way it would in
the inbox.
"""

from __future__ import annotations

import datetime as dt
from collections import defaultdict
from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING

from mdia.domain.periods import Period

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    from mdia.domain.opportunities import Opportunity

    from mdia_eval.replay import Run
    from mdia_eval.truth import Event

# One missing day is the same alert coming back, not a new one.
MAX_GAP_DAYS = 2

type Sighting = tuple[dt.date, Opportunity]


@dataclass(frozen=True, slots=True)
class Episode:
    """One opportunity key, open from ``detected_on`` to ``closed_on``."""

    key: str
    entity: str
    kind: str
    detected_on: dt.date
    closed_on: dt.date
    # Union of the detection windows the episode covered.
    window: Period
    metrics: frozenset[str]
    detectors: frozenset[str]
    peak_score: float
    days_open: int

    def matches(self, event: Event) -> bool:
        """Whether this episode is MDIA's version of ``event``."""
        if not self.window.overlaps(event.window):
            return False
        if self.kind != event.kind_expected:
            return False
        if event.entities and self.entity not in event.entities:
            return False
        if event.detectors:
            return bool(self.detectors & event.detectors)
        return bool(self.metrics & event.metrics)


@dataclass(frozen=True, slots=True)
class Score:
    """FR-13.1 in one object; ``recall_by_kind`` is what threshold tuning reads."""

    episodes: int
    detected: list[tuple[Event, Episode]] = field(default_factory=list)
    missed: list[Event] = field(default_factory=list)
    # Alerts that match no injected scenario: the false positives, kept for tuning.
    unexplained: list[Episode] = field(default_factory=list)
    # Injected scenarios inside a festive window, where staying quiet is the design.
    suppressed: list[Event] = field(default_factory=list)
    # Scenarios that ended before the replay's first detection window could see them.
    out_of_range: list[Event] = field(default_factory=list)
    quiet_windows: int = 0
    noisy_windows: int = 0

    @property
    def injected(self) -> int:
        return len(self.detected) + len(self.missed)

    @property
    def precision(self) -> float:
        return _ratio(self.episodes - len(self.unexplained), self.episodes)

    @property
    def recall(self) -> float:
        return _ratio(len(self.detected), self.injected)

    @property
    def f1(self) -> float:
        total = self.precision + self.recall
        return 0.0 if total == 0 else 2 * self.precision * self.recall / total

    @property
    def days_to_detect(self) -> list[int]:
        """How long after each scenario started MDIA first raised it."""
        return sorted(lag(event, found) for event, found in self.detected)

    @property
    def false_alarm_rate(self) -> float:
        """Share of no-issue windows that produced an unexplained alert."""
        return _ratio(self.noisy_windows, self.quiet_windows)

    def recall_within(self, days: int) -> float:
        """§13 reads recall as detection *within three days*, so lateness is a miss."""
        quick = sum(1 for event, found in self.detected if lag(event, found) <= days)
        return _ratio(quick, self.injected)

    def recall_by_kind(self, within: int | None = None) -> dict[str, tuple[int, int]]:
        """Scenario type → (detected, injected), the suppressed ones left out."""
        counts: dict[str, list[int]] = defaultdict(lambda: [0, 0])
        for event, found in self.detected:
            counts[event.kind][0] += within is None or lag(event, found) <= within
            counts[event.kind][1] += 1
        for event in self.missed:
            counts[event.kind][1] += 1
        return {kind: (hit, total) for kind, (hit, total) in sorted(counts.items())}


def episodes(runs: Sequence[Run], *, max_gap_days: int = MAX_GAP_DAYS) -> list[Episode]:
    """Collapse the per-day opportunities into one episode per uninterrupted run."""
    seen: dict[str, list[Sighting]] = defaultdict(list)
    for run in runs:
        for opportunity in run.opportunities:
            seen[opportunity.key].append((run.as_of, opportunity))
    found = [_episode(streak) for days in seen.values() for streak in _streaks(days, max_gap_days)]
    return sorted(found, key=lambda episode: episode.detected_on)


def score(found: Iterable[Episode], events: Sequence[Event], seen: Period | None = None) -> Score:
    """Match episodes to injected scenarios, then count both kinds of mistake.

    ``seen`` is the stretch the replay could detect anything in; scenarios outside it
    are set aside rather than counted as misses.
    """
    raised = list(found)
    visible = {event.id for event in events if seen is None or seen.overlaps(event.window)}
    in_range = [event for event in events if event.id in visible]
    injected = [event for event in in_range if event.injected]
    quiet = [event for event in in_range if not event.injected]

    detected: list[tuple[Event, Episode]] = []
    missed: list[Event] = []
    explained: set[int] = set()
    for event in injected:
        hits = [(index, e) for index, e in enumerate(raised) if e.matches(event)]
        if not hits:
            missed.append(event)
            continue
        explained.update(index for index, _ in hits)
        detected.append((event, min((e for _, e in hits), key=lambda e: e.detected_on)))

    unexplained = [e for index, e in enumerate(raised) if index not in explained]
    # A quiet week is noisy when a *new* alert appears in it; one still open from the
    # week before is the earlier finding, not a fresh false alarm.
    noisy = sum(
        any(event.window.start <= e.detected_on <= event.window.end for e in unexplained)
        for event in quiet
    )
    return Score(
        episodes=len(raised),
        detected=detected,
        missed=missed,
        unexplained=unexplained,
        out_of_range=[e for e in events if e.injected and e.id not in visible],
        quiet_windows=len(quiet),
        noisy_windows=noisy,
    )


def split_suppressed(result: Score, festive: Sequence[Period]) -> Score:
    """Move missed scenarios that fall in a festive window into their own bucket.

    Staying quiet during a declared sale is the product's intent (FR-6.2), so counting
    those as recall failures would measure the opposite of what was built.
    """
    if not festive:
        return result
    by_design = {
        event.id
        for event in result.missed
        if any(event.window.overlaps(window) for window in festive)
    }
    return replace(
        result,
        missed=[event for event in result.missed if event.id not in by_design],
        suppressed=[event for event in result.missed if event.id in by_design],
    )


def _streaks(days: Sequence[Sighting], max_gap_days: int) -> list[list[Sighting]]:
    streaks: list[list[Sighting]] = []
    for sighting in sorted(days, key=lambda pair: pair[0]):
        if streaks and (sighting[0] - streaks[-1][-1][0]).days <= max_gap_days:
            streaks[-1].append(sighting)
        else:
            streaks.append([sighting])
    return streaks


def _episode(streak: Sequence[Sighting]) -> Episode:
    seen = [opportunity for _, opportunity in streak]
    first = seen[0]
    signals = [signal for opportunity in seen for signal in opportunity.signals]
    return Episode(
        key=first.key,
        entity=first.entity.id,
        kind=first.kind,
        detected_on=streak[0][0],
        closed_on=streak[-1][0],
        window=Period(
            min(opportunity.window.start for opportunity in seen),
            max(opportunity.window.end for opportunity in seen),
        ),
        metrics=frozenset(signal.metric for signal in signals),
        detectors=frozenset(signal.detector for signal in signals),
        peak_score=max(opportunity.score for opportunity in seen),
        days_open=len(streak),
    )


def lag(event: Event, found: Episode) -> int:
    """Days between the scenario's first day and the first alert about it."""
    return (found.detected_on - event.window.start).days


def _ratio(part: int, whole: int) -> float:
    return 0.0 if whole == 0 else part / whole
