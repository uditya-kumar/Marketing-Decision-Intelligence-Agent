"""The grounding guard (FR-8.3): an answer may contain only what it was given.

Three checks, in the order they are cheap: every signal ID cited exists, the action is
one the catalogue allows on this entity, and every number in the prose appears in the
evidence. The third is the point of the whole system — a diagnosis that quotes a CPA
nobody computed is exactly the failure MDIA exists to avoid.

Violations come back as sentences, because they are fed straight back to the model as
the feedback for its one retry.
"""

from __future__ import annotations

import math
import re
from typing import TYPE_CHECKING

from mdia.domain.diagnosis import as_shown
from mdia.domain.recommendations import ACTIONS, allowed

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator

    from mdia.agents.schemas import LlmDiagnosis
    from mdia.domain.diagnosis import Evidence, Node

# A quoted number may be rounded, but not by more than this.
TOLERANCE_PCT = 2.0
# Absolute slack, so "48%" still matches a 48.4% change and "₹612" a ₹611.80 CPA.
TOLERANCE_ABS = 0.5

# What a number can be written in: a rate, a multiple, or rupees in Indian units.
_SCALES: dict[str, float] = {"l": 1e5, "lakh": 1e5, "lakhs": 1e5, "cr": 1e7, "crore": 1e7}
_NUMBER = re.compile(
    r"(?<![\w.])(\d[\d,]*(?:\.\d+)?)\s*(%|x|l\b|lakhs?\b|cr\b|crore\b)?", re.IGNORECASE
)


def check(output: LlmDiagnosis, evidence: Evidence) -> list[str]:
    """Everything wrong with the answer; empty means it is grounded."""
    return [
        *_bad_ids(output, evidence),
        *_bad_action(output, evidence),
        *_bad_numbers(output, evidence),
    ]


def allowed_numbers(evidence: Evidence) -> set[float]:
    """Every number the answer is allowed to quote, as a reader would see it."""
    found: set[float] = {float(evidence.window.days), float(evidence.impact)}
    for signal in evidence.signals:
        for value in (signal.current, signal.baseline):
            if value is not None:
                found.update({value, as_shown(signal.metric, value)})
        found.update(
            value for value in (signal.change_pct, signal.impact, signal.score) if value is not None
        )
        found.update(signal.measures.values())
        found.update(signal.baseline_measures.values())
    for node in _nodes(evidence.tree):
        for value in (node.before, node.after):
            if value is not None:
                found.update({value, as_shown(node.metric, value)})
        found.update(value for value in (node.change_pct, node.share_pct) if value is not None)
    # Counting the evidence itself is fair: "two of the three signals agree".
    found.update(float(count) for count in range(len(evidence.signals) + 1))
    date = evidence.window.end
    found.update({float(date.day), float(date.month), float(date.year)})
    return {abs(value) for value in found}


def numbers_in(text: str, *, ignore: Iterable[str] = ()) -> list[float]:
    """The numbers a reader would take from ``text``, with signal IDs removed first."""
    for token in ignore:
        text = text.replace(token, " ")
    found = []
    for digits, unit in _NUMBER.findall(text):
        value = float(digits.replace(",", ""))
        scale = _SCALES.get(unit.lower())
        # Both forms count as quoted: "₹3.4 lakh" and a bare "3.4" next to it are the
        # same claim, and only one of them is in the evidence as a number.
        found.append(value * scale if scale else value)
        if scale:
            found.append(value)
    return found


def _bad_ids(output: LlmDiagnosis, evidence: Evidence) -> Iterator[str]:
    known = set(evidence.signal_ids)
    cited = {
        signal_id
        for hypothesis in output.hypotheses
        for signal_id in hypothesis.evidence_signal_ids
    }
    for signal_id in sorted(cited - known):
        yield f"Signal ID {signal_id!r} is not in the evidence; cite the IDs exactly as given."


def _bad_action(output: LlmDiagnosis, evidence: Evidence) -> Iterator[str]:
    action = output.action_type
    if action not in ACTIONS:
        yield f"{action!r} is not an action in the catalogue."
    elif not allowed(action, evidence):
        reason = (
            "that campaign is protected"
            if evidence.protected
            else f"it cannot be taken on a {evidence.entity.level}"
        )
        yield f"The action {action!r} is not available here: {reason}."


def _bad_numbers(output: LlmDiagnosis, evidence: Evidence) -> Iterator[str]:
    permitted = allowed_numbers(evidence)
    ids = evidence.signal_ids
    for field, text in _texts(output):
        for value in numbers_in(text, ignore=ids):
            if not _matches(value, permitted):
                yield (
                    f"The {field} quotes {value:g}, which is not in the evidence;"
                    " use only the numbers given."
                )
                break


def _texts(output: LlmDiagnosis) -> Iterator[tuple[str, str]]:
    yield "observation", output.observation
    yield "action rationale", output.action_rationale
    for index, hypothesis in enumerate(output.hypotheses, start=1):
        yield f"statement for hypothesis {index}", hypothesis.statement
    for index, alternative in enumerate(output.alternative_explanations, start=1):
        yield f"alternative explanation {index}", alternative


def _matches(value: float, permitted: Iterable[float]) -> bool:
    return any(
        math.isclose(abs(value), other, rel_tol=TOLERANCE_PCT / 100, abs_tol=TOLERANCE_ABS)
        for other in permitted
    )


def _nodes(node: Node) -> Iterator[Node]:
    yield node
    for child in node.children:
        yield from _nodes(child)
