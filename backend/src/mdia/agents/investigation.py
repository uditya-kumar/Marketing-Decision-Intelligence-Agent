"""The investigation graph (FR-8): evidence, a diagnosis, and a recommendation.

``build_evidence → diagnose → ground_check → (retry twice | rules fallback) → finalize``

The LLM occupies exactly one node of this, and even there it only ranks and phrases what
the evidence already says. Everything numeric — the tree, the confidence, the guardrail,
the priority — is computed in ``domain/`` by ``finalize``, whichever way the diagnosis
was reached. That is what makes the fallback a degradation in wording only (NFR-5).
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
from mdia.agents.prompts import DIAGNOSIS_PROMPT_VERSION, DIAGNOSIS_SYSTEM, retry_prompt
from mdia.agents.prompts import diagnosis_prompt as render
from mdia.agents.schemas import LlmDiagnosis

# ``Evidence``, ``Opportunity`` and ``TrustStatus`` are annotations only, but ``StateGraph``
# resolves the state TypedDict's hints when the graph is built, so they must exist at runtime.
from mdia.domain.diagnosis import Diagnosis, Evidence, Hypothesis, build_evidence, diagnose
from mdia.domain.opportunities import Opportunity  # noqa: TC001
from mdia.domain.recommendations import confidence_of, priority, recommend
from mdia.domain.trust import TrustStatus  # noqa: TC001

if TYPE_CHECKING:
    from collections.abc import Collection, Sequence

    from langchain_core.language_models import BaseChatModel
    from langgraph.graph.state import CompiledStateGraph

    from mdia.domain.recommendations import Recommendation

log = structlog.get_logger(__name__)

PURPOSE = "diagnosis"
# FR-8.3: the first answer plus at most two more, each told what was wrong with the last.
MAX_RETRIES = 2
# Throttling and a dropped connection are the LLM's weather, not an answer we can use.
RETRY_POLICY = RetryPolicy(max_attempts=3, initial_interval=1.0)

DiagnosisSource = Literal["llm", "rules"]


class InvestigationState(TypedDict, total=False):
    """Nodes get their data passed in; nothing here reaches the database."""

    opportunity: Opportunity
    trust: TrustStatus
    protected: tuple[str, ...]
    evidence: Evidence
    prompt: str
    answer: LlmDiagnosis | None
    violations: list[str]
    attempts: int
    calls: Annotated[list[CallRecord], operator.add]
    result: Investigation


@dataclass(frozen=True, slots=True)
class Investigation:
    """What the graph produces for one opportunity, ready for the service to store."""

    evidence: Evidence
    diagnosis: Diagnosis
    recommendation: Recommendation | None
    confidence: float
    priority: float
    source: DiagnosisSource
    calls: tuple[CallRecord, ...]


if TYPE_CHECKING:
    type Graph = CompiledStateGraph[InvestigationState, Any, InvestigationState, InvestigationState]


def build_investigation(model: BaseChatModel | None) -> Graph:
    """Compile the graph. ``model`` of ``None`` makes every investigation rule-based."""

    def diagnose_node(state: InvestigationState) -> InvestigationState:
        """The one LLM node. Raises on transport failure, so ``RETRY_POLICY`` applies."""
        if model is None:  # pragma: no cover - the graph routes around this node
            return {"answer": None}
        attempt = state.get("attempts", 0) + 1
        violations = state.get("violations") or []
        prompt = state["prompt"]
        completion = structured(
            model,
            LlmDiagnosis,
            retry_prompt(prompt, violations) if violations else prompt,
            system=DIAGNOSIS_SYSTEM,
            purpose=PURPOSE,
            prompt_version=DIAGNOSIS_PROMPT_VERSION,
            attempt=attempt,
        )
        return {"answer": completion.output, "attempts": attempt, "calls": [completion.record]}

    def route(state: InvestigationState) -> Literal["diagnose", "finalize"]:
        if not state.get("violations"):
            return "finalize"
        return "diagnose" if state.get("attempts", 0) <= MAX_RETRIES else "finalize"

    def start(state: InvestigationState) -> Literal["diagnose", "finalize"]:
        return "finalize" if model is None else "diagnose"

    builder = StateGraph(InvestigationState)
    builder.add_node("build_evidence", _build_evidence)
    builder.add_node("diagnose", diagnose_node, retry_policy=RETRY_POLICY)
    builder.add_node("ground_check", _ground_check)
    builder.add_node("finalize", _finalize)
    builder.add_edge(START, "build_evidence")
    builder.add_conditional_edges("build_evidence", start, ["diagnose", "finalize"])
    builder.add_edge("diagnose", "ground_check")
    builder.add_conditional_edges("ground_check", route, ["diagnose", "finalize"])
    builder.add_edge("finalize", END)
    return builder.compile()


def investigate(
    graph: Graph,
    opportunity: Opportunity,
    *,
    trust: TrustStatus = "ok",
    protected: Collection[str] = (),
) -> Investigation:
    """Investigate one opportunity. Never raises: the rules are always an answer."""
    state: InvestigationState = {
        "opportunity": opportunity,
        "trust": trust,
        "protected": tuple(protected),
        "violations": [],
        "attempts": 0,
        "calls": [],
    }
    try:
        result: Investigation = graph.invoke(state)["result"]
    except Exception as error:
        # The analysis must never block on the LLM (NFR-5), whatever went wrong in there.
        log.warning("investigation.failed", key=opportunity.key, error=str(error))
        evidence = build_evidence(opportunity, trust=trust, protected=protected)
        failed = failure_record(PURPOSE, DIAGNOSIS_PROMPT_VERSION, str(error))
        return _result(evidence, diagnose(evidence), "rules", calls=(failed,))
    return result


def _build_evidence(state: InvestigationState) -> InvestigationState:
    evidence = build_evidence(
        state["opportunity"], trust=state.get("trust", "ok"), protected=state.get("protected", ())
    )
    return {"evidence": evidence, "prompt": render(evidence)}


def _ground_check(state: InvestigationState) -> InvestigationState:
    answer, evidence = state.get("answer"), state["evidence"]
    if answer is None:
        return {"violations": ["The answer did not match the required schema."]}
    violations = grounding.check(answer, evidence)
    if violations:
        log.info("grounding.rejected", key=state["opportunity"].key, violations=violations)
    return {"violations": violations}


def _finalize(state: InvestigationState) -> InvestigationState:
    """Confidence, the guardrail and the priority in code, whoever wrote the words."""
    evidence = state["evidence"]
    answer = state.get("answer")
    grounded = answer is not None and not state.get("violations")
    diagnosis = _from_llm(answer) if grounded and answer else diagnose(evidence)
    source: DiagnosisSource = "llm" if grounded else "rules"
    calls = _stamp(state.get("calls", []), grounded=grounded)
    return {"result": _result(evidence, diagnosis, source, calls=calls, answer=answer)}


def _from_llm(answer: LlmDiagnosis) -> Diagnosis:
    """The model's words as a domain diagnosis, now that they are known to be grounded."""
    return Diagnosis(
        observation=answer.observation,
        hypotheses=tuple(
            Hypothesis(item.cause, item.statement, tuple(item.evidence_signal_ids))
            for item in answer.hypotheses
        ),
        alternatives=tuple(answer.alternative_explanations),
    )


def _result(
    evidence: Evidence,
    diagnosis: Diagnosis,
    source: DiagnosisSource,
    *,
    calls: Sequence[CallRecord] = (),
    answer: LlmDiagnosis | None = None,
) -> Investigation:
    chosen = answer.action_type if answer is not None and source == "llm" else None
    rationale = answer.action_rationale if answer is not None and source == "llm" else ""
    sure = confidence_of(evidence)
    return Investigation(
        evidence=evidence,
        diagnosis=diagnosis,
        recommendation=recommend(diagnosis, evidence, action=chosen, rationale=rationale),
        confidence=sure,
        priority=priority(evidence.impact, sure),
        source=source,
        calls=tuple(calls),
    )


def _stamp(calls: Sequence[CallRecord], *, grounded: bool) -> list[CallRecord]:
    """Record how each call ended: only the last one can be the grounded answer."""
    if not calls:
        return []
    *earlier, final = calls
    return [
        *(replace(call, grounded=False, fallback=not grounded) for call in earlier),
        replace(final, grounded=grounded, fallback=not grounded),
    ]
