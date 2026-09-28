"""Rendering the rest of §13: diagnosis, trust, grounding, and the scorecard itself.

Detection has its own renderer in :mod:`mdia_eval.report`; this module reads the same
way, so the thesis can paste any of them side by side.
"""

from __future__ import annotations

import statistics
from typing import TYPE_CHECKING

from mdia_eval.detection import lag
from mdia_eval.diagnosis import TARGET_TOP3
from mdia_eval.grounding import TARGET_LEAKED
from mdia_eval.report import (
    TARGET_DAYS_TO_DETECT,
    TARGET_FALSE_ALARM,
    TARGET_RECALL,
    pct,
    verdict,
)
from mdia_eval.trust import TARGET_ACCURACY

if TYPE_CHECKING:
    from collections.abc import Iterator

    from mdia_eval.detection import Score
    from mdia_eval.diagnosis import DiagnosisScore
    from mdia_eval.grounding import GroundingScore
    from mdia_eval.trust import TrustScore

WIDTH = 64


def diagnosis(result: DiagnosisScore, other: DiagnosisScore | None = None) -> str:
    """FR-13.2, optionally with the rule-based run of the same cases beside it."""
    return "\n".join(_diagnosis_lines(result, other))


def _diagnosis_lines(result: DiagnosisScore, other: DiagnosisScore | None) -> Iterator[str]:
    yield "FR-13.2 Diagnosis accuracy"
    yield "=" * WIDTH
    yield f"Scenarios diagnosed: {len(result.cases)} ({result.source})"
    runs = [result] if other is None else [result, other]
    if other is not None:
        yield _columns("", [run.source for run in runs])
    yield _columns("Right cause, top 3", [pct(run.top3) for run in runs])
    yield _columns("Right cause, top 1", [pct(run.top1) for run in runs])
    yield _columns("Right action", [pct(run.action_accuracy) for run in runs])
    yield f"{'':<26}{verdict(result.top3 >= TARGET_TOP3)} on top 3  (section 13)"
    yield ""
    yield f"{'Scenario type':<26}{'top 1':<12}{'top 3':<12}"
    for kind, (one, three, total) in result.by_kind().items():
        yield f"  {kind:<24}{f'{one}/{total}':<12}{f'{three}/{total}':<12}{pct(three / total)}"
    if result.missed:
        yield ""
        yield "Cause not in the top three"
        for case in result.missed:
            said = ", ".join(case.causes[:3]) or "nothing"
            yield f"  {case.event_id:<10}{case.kind:<22}said {said}"


def trust(result: TrustScore) -> str:
    """FR-13.3."""
    return "\n".join(_trust_lines(result))


def _trust_lines(result: TrustScore) -> Iterator[str]:
    lags = [b.lag_days for b in result.breaks if b.lag_days is not None]
    yield "FR-13.3 Tracking breaks"
    yield "=" * WIDTH
    yield f"Breaks injected: {len(result.breaks)} scored"
    if result.uncovered:
        yield f"{len(result.uncovered)} ended before the replay's first window, not scored"
    yield ""
    caught = f"{sum(b.caught for b in result.breaks)} of {len(result.breaks)}"
    yield (
        f"{'Break caught':<26}{pct(result.accuracy)}  {caught}  "
        f"{verdict(result.accuracy >= TARGET_ACCURACY)}  (section 13)"
    )
    yield (
        f"{'Advice suppressed too':<26}{pct(result.suppression)}  "
        f"{verdict(result.suppression >= TARGET_ACCURACY)}  (section 13)"
    )
    yield (
        f"{'False alarms':<26}{pct(result.false_alarm_rate)} of "
        f"{result.judged_days} channel-days judged"
    )
    if lags:
        yield ""
        yield "Days to call a break"
        yield f"{'  median':<26}{statistics.median(lags):.0f}"
        yield f"{'  worst':<26}{max(lags)}"
    if result.missed:
        yield ""
        yield "Never called broken"
        for item in result.missed:
            yield f"  {item.event_id:<10}{item.channel or 'account':<22}{item.window_days}d window"
    if result.leaked:
        yield ""
        yield "Advice that escaped while the pixel was broken"
        for item in result.leaked:
            yield f"  {item.event_id:<10}{item.channel or 'account':<22}{', '.join(item.leaked)}"


def grounding(result: GroundingScore) -> str:
    """FR-13.4."""
    return "\n".join(_grounding_lines(result))


def _grounding_lines(result: GroundingScore) -> Iterator[str]:
    yield "FR-13.4 Grounding"
    yield "=" * WIDTH
    yield f"Model answers asked for: {result.answers} over {result.attempts} calls"
    yield ""
    yield f"{'Violations before the guard':<30}{pct(result.violation_rate)} of attempts"
    yield f"{'Saved by a retry':<30}{result.recovered} of {result.retries} retries"
    yield f"{'Ended rule-based instead':<30}{pct(result.fallback_rate)} of answers"
    yield f"{'Transport or schema errors':<30}{result.errors}"
    yield (
        f"{'Ungrounded numbers shown':<30}{result.leaked}  "
        f"{verdict(result.leaked <= TARGET_LEAKED)}  (section 13)"
    )
    by_purpose = result.by_purpose()
    if len(by_purpose) > 1:
        yield ""
        yield f"{'Purpose':<30}{'answers':<10}{'violations':<12}{'rule-based':<12}"
        for purpose, part in by_purpose.items():
            yield (
                f"  {purpose:<28}{part.answers:<10}{pct(part.violation_rate):<12}"
                f"{pct(part.fallback_rate):<12}"
            )


def scorecard(
    detected: Score,
    *,
    diagnosed: DiagnosisScore | None = None,
    trusted: TrustScore | None = None,
    grounded: GroundingScore | None = None,
) -> str:
    """Every §13 criterion on one page, as the thesis reports it."""
    return "\n".join(_scorecard_lines(detected, diagnosed, trusted, grounded))


def _scorecard_lines(
    detected: Score,
    diagnosed: DiagnosisScore | None,
    trusted: TrustScore | None,
    grounded: GroundingScore | None,
) -> Iterator[str]:
    quick = detected.recall_within(TARGET_DAYS_TO_DETECT)
    yield "Section 13 scorecard"
    yield "=" * WIDTH
    yield f"{'Criterion':<34}{'Target':<12}{'Measured':<12}"
    yield _row("Detection within 3 days", f">= {pct(TARGET_RECALL)}", quick, quick >= TARGET_RECALL)
    yield _row(
        "False alarms",
        f"< {pct(TARGET_FALSE_ALARM)}",
        detected.false_alarm_rate,
        detected.false_alarm_rate < TARGET_FALSE_ALARM,
    )
    if diagnosed is not None:
        yield _row(
            "Cause in the top three",
            f">= {pct(TARGET_TOP3)}",
            diagnosed.top3,
            diagnosed.top3 >= TARGET_TOP3,
        )
    if trusted is not None:
        yield _row(
            "Tracking breaks caught",
            f">= {pct(TARGET_ACCURACY)}",
            trusted.accuracy,
            trusted.accuracy >= TARGET_ACCURACY,
        )
        yield _row(
            "Advice suppressed while broken",
            f">= {pct(TARGET_ACCURACY)}",
            trusted.suppression,
            trusted.suppression >= TARGET_ACCURACY,
        )
    if grounded is not None:
        yield (
            f"{'Ungrounded numbers shown':<34}{'0':<12}{grounded.leaked:<12}"
            f"{verdict(grounded.leaked <= TARGET_LEAKED)}"
        )
    if detected.missed:
        yield ""
        yield f"Scenarios never detected: {len(detected.missed)} of {detected.injected}"
    late = [pair for pair in detected.detected if lag(*pair) > TARGET_DAYS_TO_DETECT]
    if late:
        yield f"Scenarios detected late: {len(late)}"


def _columns(name: str, values: list[str]) -> str:
    return f"{name:<26}" + "".join(f"{value:<12}" for value in values)


def _row(name: str, target: str, value: float, passed: bool) -> str:
    return f"{name:<34}{target:<12}{pct(value):<12}{verdict(passed)}"
