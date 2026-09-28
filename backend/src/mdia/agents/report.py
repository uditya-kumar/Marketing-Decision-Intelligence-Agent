"""The weekly report graph (FR-11.2): the week's facts, narrated.

``narrate → ground_check → (retry twice | template fallback)``

The payload is already complete when it arrives here; the model only rewrites it. So
the failure mode is mild by construction: if it invents a number, or never answers, the
report falls back to ``domain/report_text.template`` and the reader loses the phrasing,
not the week.
"""

from __future__ import annotations

import operator
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Annotated, Any, Literal, TypedDict

import structlog
from langgraph.graph import END, START, StateGraph
from langgraph.types import RetryPolicy

from mdia.agents import grounding
from mdia.agents.llm import CallRecord, failure_record, structured
from mdia.agents.prompts import REPORT_PROMPT_VERSION, REPORT_SYSTEM, report_prompt, retry_prompt
from mdia.agents.schemas import LlmReport
from mdia.domain.report_text import ReportText, template

# An annotation only, but ``StateGraph`` resolves the state's hints when it is built.
from mdia.domain.reports import WeeklyPayload  # noqa: TC001

if TYPE_CHECKING:
    from collections.abc import Sequence

    from langchain_core.language_models import BaseChatModel
    from langgraph.graph.state import CompiledStateGraph

log = structlog.get_logger(__name__)

PURPOSE = "report"
# The first narrative plus at most two more, each told which number was invented.
MAX_RETRIES = 2
RETRY_POLICY = RetryPolicy(max_attempts=3, initial_interval=1.0)

ReportSource = Literal["llm", "template"]


class ReportState(TypedDict, total=False):
    """Nodes get the payload passed in; nothing here reaches the database."""

    payload: WeeklyPayload
    prompt: str
    answer: LlmReport | None
    violations: list[str]
    attempts: int
    calls: Annotated[list[CallRecord], operator.add]
    result: Report


@dataclass(frozen=True, slots=True)
class Report:
    """One week's narrative, ready for the service to store beside its payload."""

    text: ReportText
    source: ReportSource
    grounded: bool
    calls: tuple[CallRecord, ...]


if TYPE_CHECKING:
    type Graph = CompiledStateGraph[ReportState, Any, ReportState, ReportState]


def build_report(model: BaseChatModel | None) -> Graph:
    """Compile the graph. ``model`` of ``None`` makes every report template-written."""

    def narrate(state: ReportState) -> ReportState:
        """The one LLM node. Raises on transport failure, so ``RETRY_POLICY`` applies."""
        if model is None:  # pragma: no cover - the graph routes around this node
            return {"answer": None}
        attempt = state.get("attempts", 0) + 1
        violations = state.get("violations") or []
        prompt = state["prompt"]
        completion = structured(
            model,
            LlmReport,
            retry_prompt(prompt, violations) if violations else prompt,
            system=REPORT_SYSTEM,
            purpose=PURPOSE,
            prompt_version=REPORT_PROMPT_VERSION,
            attempt=attempt,
        )
        return {"answer": completion.output, "attempts": attempt, "calls": [completion.record]}

    def route(state: ReportState) -> Literal["narrate", "finalize"]:
        if not state.get("violations"):
            return "finalize"
        return "narrate" if state.get("attempts", 0) <= MAX_RETRIES else "finalize"

    def start(state: ReportState) -> Literal["narrate", "finalize"]:
        return "finalize" if model is None else "narrate"

    builder = StateGraph(ReportState)
    builder.add_node("prepare", _prepare)
    builder.add_node("narrate", narrate, retry_policy=RETRY_POLICY)
    builder.add_node("ground_check", _ground_check)
    builder.add_node("finalize", _finalize)
    builder.add_edge(START, "prepare")
    builder.add_conditional_edges("prepare", start, ["narrate", "finalize"])
    builder.add_edge("narrate", "ground_check")
    builder.add_conditional_edges("ground_check", route, ["narrate", "finalize"])
    builder.add_edge("finalize", END)
    return builder.compile()


def write_report(graph: Graph, payload: WeeklyPayload) -> Report:
    """Narrate one week. Never raises: the template is always a report."""
    state: ReportState = {"payload": payload, "violations": [], "attempts": 0, "calls": []}
    try:
        result: Report = graph.invoke(state)["result"]
    except Exception as error:
        log.warning("report.failed", week=str(payload.week.end), error=str(error))
        failed = failure_record(PURPOSE, REPORT_PROMPT_VERSION, str(error))
        return Report(template(payload), "template", grounded=False, calls=(failed,))
    return result


def _prepare(state: ReportState) -> ReportState:
    return {"prompt": report_prompt(state["payload"])}


def _ground_check(state: ReportState) -> ReportState:
    answer, payload = state.get("answer"), state["payload"]
    if answer is None:
        return {"violations": ["The answer did not match the required schema."]}
    violations = grounding.check_report(answer, payload)
    if violations:
        log.info("grounding.rejected", purpose=PURPOSE, violations=violations)
    return {"violations": violations}


def _finalize(state: ReportState) -> ReportState:
    answer = state.get("answer")
    grounded = answer is not None and not state.get("violations")
    text = ReportText(answer.summary, answer.detail) if grounded and answer else None
    return {
        "result": Report(
            text=text or template(state["payload"]),
            source="llm" if grounded else "template",
            grounded=grounded,
            calls=tuple(_stamp(state.get("calls", []), grounded=grounded)),
        )
    }


def _stamp(calls: Sequence[CallRecord], *, grounded: bool) -> list[CallRecord]:
    """Record how each call ended: only the last one can be the grounded answer."""
    if not calls:
        return []
    *earlier, final = calls
    return [
        *(replace(call, grounded=False, fallback=not grounded) for call in earlier),
        replace(final, grounded=grounded, fallback=not grounded),
    ]
