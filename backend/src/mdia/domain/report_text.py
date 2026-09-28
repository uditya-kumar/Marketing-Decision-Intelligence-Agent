"""The report in words, computed from the payload (FR-11.2's fallback).

Two jobs, one set of sentences: this is what the reader sees when the model is
unavailable or ungrounded, and it is also how the payload is shown to the model, so a
narration can only ever rephrase facts that are already written here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from mdia.domain.kpi import label
from mdia.domain.wording import moved, rupees, value_text

if TYPE_CHECKING:
    import datetime as dt

    from mdia.domain.kpi import Metric
    from mdia.domain.reports import (
        DecisionLine,
        ExperimentLine,
        KpiLine,
        OpportunityLine,
        PacingLine,
        WeeklyPayload,
    )

GOAL_WORDS = {"ahead": "ahead of goal", "on_track": "on track", "behind": "behind goal"}
PACE_WORDS = {"on_track": "on plan", "over": "over pace", "under": "under pace"}
VERDICT_WORDS = {
    "worked": "worked",
    "did_not_work": "did not work",
    "inconclusive": "was inconclusive",
}
DECISION_WORDS = {"approve": "Approved", "reject": "Rejected", "dismiss": "Dismissed"}


@dataclass(frozen=True, slots=True)
class ReportText:
    """The report's prose: a founder summary, then the detail for the team (UI.md §5.6)."""

    summary: list[str]
    detail: list[str]


def template(payload: WeeklyPayload) -> ReportText:
    """The whole report written from the payload alone, with no model involved."""
    return ReportText(summary=_summary(payload), detail=_detail(payload))


def kpi_line(line: KpiLine) -> str:
    """Revenue ₹16.40 L, fell 21% on last week, behind goal ₹18.70 L."""
    # The line opens a sentence, and half the metric labels are ordinary words.
    parts = [f"{_cap(label(line.metric))} {_value(line.metric, line.value)}"]
    if line.change_pct is not None:
        parts.append(f"{moved(line.change_pct)} on last week")
    if line.target is not None and line.goal_status is not None:
        parts.append(f"{GOAL_WORDS[line.goal_status]} {_value(line.metric, line.target)}")
    if not line.reliable:
        parts.append("not reliable while tracking is broken")
    return ", ".join(parts)


def pacing_line(row: PacingLine) -> str:
    pace = row.pacing
    spent = f"{pace.spent_pct:.0f}% of {rupees(pace.budget)} spent"
    month = f"{pace.month_elapsed_pct:.0f}% of the month gone"
    line = f"{row.label}: {spent} with {month}, {PACE_WORDS[pace.status]}"
    if pace.suggested_daily is None:
        return line
    return f"{line}; {rupees(pace.suggested_daily)} a day lands on budget"


def opportunity_line(row: OpportunityLine) -> str:
    movement = f"{label(row.metric)} {_value(row.metric, row.current)}"
    if row.baseline is not None:
        movement += f" against {_value(row.metric, row.baseline)}"
    if row.change_pct is not None:
        movement += f" ({moved(row.change_pct)})"
    return f"{row.band.upper()} {row.title}: {movement}, {rupees(abs(row.impact))} a week at stake"


def experiment_line(row: ExperimentLine) -> str:
    if row.verdict is None:
        return f"{row.title}: still being measured"
    days = "" if row.sample_days is None else f" over {row.sample_days} days"
    movement = f"{_value(row.metric, row.before)} to {_value(row.metric, row.after)}"
    return f"{row.title}: {label(row.metric)} {movement}{days} — {VERDICT_WORDS[row.verdict]}"


def decision_line(row: DecisionLine) -> str:
    line = f"{DECISION_WORDS.get(row.kind, row.kind)}: {row.title}"
    return line if row.reason is None else f"{line} — {row.reason}"


def week_text(day: dt.date) -> str:
    return f"{day:%d %b %Y}"


def _summary(payload: WeeklyPayload) -> list[str]:
    lines = [_headline(payload), *_goal_lines(payload)]
    if payload.issue_cost:
        issues = sum(1 for row in payload.opportunities if row.kind == "issue")
        together = " between them" if issues > 1 else ""
        lines.append(
            f"{issues} {_plural(issues, 'issue')} {'cost' if issues > 1 else 'costs'} about"
            f" {rupees(payload.issue_cost)} a week{together}."
        )
    if payload.win_upside:
        wins = sum(1 for row in payload.opportunities if row.kind == "win")
        lines.append(
            f"{wins} {_plural(wins, 'opportunity')} could add"
            f" {rupees(payload.win_upside)} a week if acted on."
        )
    lines.append(_changes(payload))
    return lines


def _headline(payload: WeeklyPayload) -> str:
    revenue = next((line for line in payload.kpis if line.metric == "store_revenue"), None)
    week = f"the {payload.week.days} days to {week_text(payload.week.end)}"
    if revenue is None or revenue.value is None:
        return f"This is the week of {week}."
    if revenue.change_pct is None:
        return f"Revenue was {rupees(revenue.value)} in {week}."
    return (
        f"Revenue was {rupees(revenue.value)} in {week},"
        f" {moved(revenue.change_pct)} on the week before."
    )


def _goal_lines(payload: WeeklyPayload) -> list[str]:
    off = [line for line in payload.kpis if line.goal_status == "behind"]
    if not off:
        return ["Every goal with a target was met or on track."]
    named = ", ".join(f"{label(line.metric)} {_value(line.metric, line.value)}" for line in off)
    return [f"Behind goal: {named}."]


def _changes(payload: WeeklyPayload) -> str:
    decided = len(payload.decisions)
    if not decided:
        return "No decisions were recorded this week."
    judged = [row for row in payload.experiments if row.verdict is not None]
    if not judged:
        return f"{decided} {_plural(decided, 'decision')} recorded, none judged yet."
    return (
        f"{decided} {_plural(decided, 'decision')} recorded;"
        f" of {len(judged)} judged, {payload.worked} worked."
    )


def _detail(payload: WeeklyPayload) -> list[str]:
    sections = [
        ("This week's KPIs", [kpi_line(line) for line in payload.kpis]),
        ("Budget pacing", [pacing_line(row) for row in payload.pacing]),
        ("What mattered", [opportunity_line(row) for row in payload.opportunities]),
        ("Changes under test", [experiment_line(row) for row in payload.experiments]),
        ("Decisions", [decision_line(row) for row in payload.decisions]),
    ]
    return [f"{heading}. " + " ".join(lines) for heading, lines in sections if lines]


def _value(metric: Metric, value: float | None) -> str:
    return "n/a" if value is None else value_text(metric, value)


def _cap(text: str) -> str:
    """Upper-case the first letter only, leaving CPA and CTR as they are."""
    return text[:1].upper() + text[1:]


def _plural(count: int, word: str) -> str:
    if count == 1:
        return word
    return f"{word[:-1]}ies" if word.endswith("y") else f"{word}s"
