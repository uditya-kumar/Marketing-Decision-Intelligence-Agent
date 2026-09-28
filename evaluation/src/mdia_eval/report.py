"""Rendering an evaluation result as plain text, with §13's targets alongside."""

from __future__ import annotations

import statistics
from typing import TYPE_CHECKING

from mdia_eval.detection import lag

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence

    from mdia_eval.detection import Score
    from mdia_eval.replay import Run

# Section 13 of the requirements, as numbers this report can check itself against.
TARGET_RECALL = 0.80
TARGET_FALSE_ALARM = 0.10
TARGET_DAYS_TO_DETECT = 3


def detection(result: Score, runs: Sequence[Run]) -> str:
    return "\n".join(_detection_lines(result, runs))


def _detection_lines(result: Score, runs: Sequence[Run]) -> Iterator[str]:
    quick = result.recall_within(TARGET_DAYS_TO_DETECT)
    days = result.days_to_detect

    yield "FR-13.1 Detection accuracy"
    yield "=" * 64
    yield f"Replayed {len(runs)} days, {runs[0].as_of} to {runs[-1].as_of}"
    yield f"Alerts raised: {result.episodes}"
    yield ""
    yield (
        f"{'Detected within 3 days':<26}{_pct(quick)}  "
        f"{_verdict(quick >= TARGET_RECALL)}  (section 13)"
    )
    seen = f"{len(result.detected)} of {result.injected}"
    yield f"{'Detected at all':<26}{_pct(result.recall)}  {seen}"
    yield f"{'Precision':<26}{_pct(result.precision)}"
    yield f"{'F1':<26}{result.f1:.2f}"
    yield (
        f"{'False alarms':<26}{_pct(result.false_alarm_rate)} of "
        f"{result.quiet_windows} no-issue windows  "
        f"{_verdict(result.false_alarm_rate < TARGET_FALSE_ALARM)}  (section 13)"
    )
    if result.suppressed:
        yield f"{'Quiet by design':<26}{len(result.suppressed)} scenarios inside a festive window"
    if result.out_of_range:
        yield f"{'Before the first window':<26}{len(result.out_of_range)} scenarios, not scored"
    yield ""
    if days:
        yield "Days to detect (from the scenario's first day)"
        yield f"{'  median':<26}{statistics.median(days):.0f}"
        yield f"{'  worst':<26}{max(days)}"
        yield ""
    yield f"{'Scenario type':<26}{'in 3 days':<12}{'at all':<12}"
    within = result.recall_by_kind(TARGET_DAYS_TO_DETECT)
    for kind, (hit, total) in result.recall_by_kind().items():
        fast = within[kind][0]
        yield f"  {kind:<24}{f'{fast}/{total}':<12}{f'{hit}/{total}':<12}{_pct(hit / total)}"
    if result.missed:
        yield ""
        yield "Missed"
        for event in result.missed:
            yield f"  {event.id:<10}{event.kind:<22}{event.window.start}..{event.window.end}"
    late = [
        (event, found)
        for event, found in result.detected
        if lag(event, found) > TARGET_DAYS_TO_DETECT
    ]
    if late:
        yield ""
        yield "Detected late"
        for event, found in sorted(late, key=lambda pair: -lag(*pair)):
            yield (
                f"  {event.id:<10}{event.kind:<22}{event.window.start}"
                f" raised {found.detected_on} ({lag(event, found)}d)"
            )


def false_positives(result: Score, top: int = 15) -> str:
    """The loudest unexplained alerts: where the thresholds need work."""
    loudest = sorted(result.unexplained, key=lambda e: e.peak_score, reverse=True)[:top]
    lines = [f"Unexplained alerts ({len(result.unexplained)}, loudest first)", "=" * 64]
    lines.extend(
        f"  {episode.detected_on}  {episode.key:<26}{episode.kind:<6}"
        f"{','.join(sorted(episode.metrics)):<30}"
        f"score {episode.peak_score:>11,.0f}  {episode.days_open}d"
        for episode in loudest
    )
    return "\n".join(lines)


def _pct(value: float) -> str:
    return f"{value * 100:.0f}%"


def _verdict(passed: bool) -> str:
    return "PASS" if passed else "FAIL"
