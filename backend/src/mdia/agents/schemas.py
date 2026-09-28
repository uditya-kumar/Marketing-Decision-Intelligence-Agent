"""What the LLM is allowed to return (FR-8.2), and nothing more.

Structured output, so a malformed answer is a validation error instead of prose to
parse. Note what is absent: no metric values, no rupees, no confidence and no
priority. Those are computed in ``domain/`` and merged in afterwards, which is why an
answer can be wrong here without a wrong number ever reaching a user.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from mdia.domain.diagnosis import Cause
from mdia.domain.recommendations import Action

MAX_HYPOTHESES = 3
MAX_ALTERNATIVES = 3
# Long enough for two sentences; a paragraph is a sign the model is padding.
MAX_TEXT = 400
# The report is read, not studied: five lines for the founder and a section each below.
MAX_SUMMARY_LINES = 5
MAX_DETAIL_SECTIONS = 6
MAX_PARAGRAPH = 700

Paragraph = Annotated[str, Field(max_length=MAX_PARAGRAPH)]


class LlmHypothesis(BaseModel):
    """One ranked reading of the evidence."""

    model_config = ConfigDict(extra="forbid")

    cause: Cause = Field(description="The cause from the fixed list that this fits.")
    statement: str = Field(
        max_length=MAX_TEXT,
        description=(
            "One or two sentences on why the evidence fits this cause. Quote only numbers"
            " that appear in the evidence, and do not claim the cause is proven."
        ),
    )
    evidence_signal_ids: list[str] = Field(
        default_factory=list,
        description="IDs of the signals this rests on, copied exactly from the evidence.",
    )


class LlmDiagnosis(BaseModel):
    """The whole of what the model contributes to an investigation."""

    model_config = ConfigDict(extra="forbid")

    observation: str = Field(
        max_length=MAX_TEXT, description="What happened, in one sentence, from the evidence only."
    )
    hypotheses: list[LlmHypothesis] = Field(
        min_length=1, max_length=MAX_HYPOTHESES, description="Most likely first."
    )
    alternative_explanations: list[str] = Field(
        default_factory=list,
        max_length=MAX_ALTERNATIVES,
        description="Readings the evidence cannot rule out.",
    )
    action_type: Action = Field(description="The single best action from the catalogue.")
    action_rationale: str = Field(
        max_length=MAX_TEXT, description="Why that action, in one or two sentences."
    )


class LlmReport(BaseModel):
    """The weekly report's prose (FR-11.2). The payload behind it is computed in code."""

    model_config = ConfigDict(extra="forbid")

    summary: list[Paragraph] = Field(
        min_length=1,
        max_length=MAX_SUMMARY_LINES,
        description=(
            "The founder summary: at most five short lines, the first answering how the"
            " week went. Quote only numbers from the report facts, exactly as written."
        ),
    )
    detail: list[Paragraph] = Field(
        min_length=1,
        max_length=MAX_DETAIL_SECTIONS,
        description=(
            "The team detail: one paragraph per section, each starting with a short"
            " heading and a full stop, in the order the facts are given."
        ),
    )

    def paragraphs(self) -> list[str]:
        """Every line the reader will see, for the grounding guard to check."""
        return [*self.summary, *self.detail]
