"""Prompts, and the evidence rendered for them. Every prompt carries a version.

The rendering is the whole of what the model may say: the grounding guard checks the
answer against the same :class:`Evidence` object this text is built from, so anything
not printed here is a fabrication by definition.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mdia.domain.diagnosis import CAUSE_LABELS
from mdia.domain.kpi import label
from mdia.domain.recommendations import ACTION_TYPES, allowed
from mdia.domain.report_text import template, week_text
from mdia.domain.wording import rupees, value_text

if TYPE_CHECKING:
    from collections.abc import Sequence

    from mdia.domain.evidence import Evidence, Node
    from mdia.domain.reports import WeeklyPayload

# Bumped whenever the wording changes, so a stored answer can be traced to its prompt.
DIAGNOSIS_PROMPT_VERSION = "diagnosis-v1"

DIAGNOSIS_SYSTEM = """You are a marketing analyst reading one week of prepared evidence.

Rules you must follow:
- Use only the evidence given. Never state a number that is not in it, and copy the
  numbers you do use exactly as they are written.
- Cite signal IDs exactly as given; never invent one.
- Choose the action from the "Actions available" list only.
- Say what the evidence is consistent with. Never claim a cause is proven.
- Be brief: one or two sentences per field, in plain language a founder would use.
"""


REPORT_PROMPT_VERSION = "report-v1"

REPORT_SYSTEM = """You are writing a marketing team's weekly report from prepared facts.

Rules you must follow:
- Use only the facts given. Never state a number that is not in them, and copy the
  numbers you do use exactly as they are written, including the ₹, % and x units.
- Never add a number of your own: no totals, no averages, no percentages you worked out.
- Do not repeat a number from a decision's reason; those are quotes, not this week's facts.
- Never say why something happened beyond what the facts say, and never promise a result.
- The summary is for a founder: at most five short lines, the first one the answer.
- The detail is for the team: one paragraph per section, keeping the section order and
  covering every row given, in plain language.
- Open each detail paragraph with that section's heading, and add no section of your own:
  the summary is already written above the detail, so never repeat it as a section.
"""


def report_prompt(payload: WeeklyPayload) -> str:
    """The week's facts as the model sees them, in the same words the fallback uses."""
    text = template(payload)
    return "\n".join(
        [
            f"Week: {payload.week.days} days to {week_text(payload.week.end)}",
            f"Issues cost this week: {rupees(payload.issue_cost)}",
            f"Opportunities not yet taken: {rupees(payload.win_upside)}",
            f"Data trust warning in force: {'yes' if payload.trust_warning else 'no'}",
            "",
            "The summary, as facts you may state and nothing else:",
            *(f"- {line}" for line in text.summary),
            "",
            "The detail sections, in this order, each already headed:",
            *(f"- {line}" for line in text.detail),
            "",
            "Write the same report in better words. Keep every number exactly as above.",
        ]
    )


def diagnosis_prompt(evidence: Evidence) -> str:
    """The evidence for one opportunity, as the model sees it."""
    entity = evidence.entity
    window = evidence.window
    return "\n".join(
        [
            f"Entity: {entity.name} ({entity.level}), {entity.channel or 'all channels'}",
            f"Window: {window.days} days to {window.end:%d %b %Y}",
            f"Kind: {evidence.kind}",
            f"Money at stake: {rupees(evidence.impact)}",
            f"Data trust for this channel: {evidence.trust}",
            f"Protected campaign (cannot be paused): {'yes' if evidence.protected else 'no'}",
            "",
            "Signals:",
            *(f"- {line}" for line in _signal_lines(evidence)),
            "",
            "Evidence tree (each driver's share of the change above it):",
            *_tree_lines(evidence.tree),
            "",
            f"Actions available: {', '.join(_actions(evidence))}",
            f"Causes to choose from: {', '.join(CAUSE_LABELS)}",
        ]
    )


def retry_prompt(prompt: str, violations: Sequence[str]) -> str:
    """The same evidence again, with what was wrong with the last answer (FR-8.3)."""
    listed = "\n".join(f"- {violation}" for violation in violations)
    return (
        f"{prompt}\n\nYour previous answer was rejected:\n{listed}\n"
        "Answer again using only the evidence above."
    )


def _signal_lines(evidence: Evidence) -> list[str]:
    return [
        f"{signal.id} | {label(signal.metric)} by {signal.detector}: "
        f"{_value(signal.metric, signal.baseline)} -> {_value(signal.metric, signal.current)}"
        f" ({_pct(signal.change_pct)}), {rupees(signal.impact)} at stake"
        for signal in evidence.signals
    ]


def _tree_lines(node: Node, depth: int = 0) -> list[str]:
    indent = "  " * depth
    share = "" if node.share_pct is None else f", share {_pct(node.share_pct)}"
    line = (
        f"{indent}- {label(node.metric)} {_pct(node.change_pct)}"
        f" ({_value(node.metric, node.before)} -> {_value(node.metric, node.after)}{share})"
    )
    return [line, *(deeper for child in node.children for deeper in _tree_lines(child, depth + 1))]


def _actions(evidence: Evidence) -> list[str]:
    available: list[str] = [action for action in ACTION_TYPES if allowed(action, evidence)]
    # An entity nothing in the catalogue applies to still needs a legal answer to give.
    return available or ["investigate_landing_page"]


def _value(metric: str, value: float | None) -> str:
    return "n/a" if value is None else value_text(metric, value)  # type: ignore[arg-type]


def _pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value:+.1f}%"
