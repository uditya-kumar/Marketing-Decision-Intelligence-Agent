"""Prompts, and the evidence rendered for them. Every prompt carries a version.

The rendering is the whole of what the model may say: the grounding guard checks the
answer against the same :class:`Evidence` object this text is built from, so anything
not printed here is a fabrication by definition.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mdia.domain.diagnosis import CAUSE_LABELS, rupees, value_text
from mdia.domain.kpi import label
from mdia.domain.recommendations import ACTION_TYPES, allowed

if TYPE_CHECKING:
    from collections.abc import Sequence

    from mdia.domain.diagnosis import Evidence, Node

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
