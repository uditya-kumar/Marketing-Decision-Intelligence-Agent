"""What the LLM is allowed to return (FR-8.2), and nothing more.

Structured output, so a malformed answer is a validation error instead of prose to
parse. Note what is absent: no metric values, no rupees, no confidence and no
priority. Those are computed in ``domain/`` and merged in afterwards, which is why an
answer can be wrong here without a wrong number ever reaching a user.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from mdia.domain.diagnosis import Cause
from mdia.domain.recommendations import Action

MAX_HYPOTHESES = 3
MAX_ALTERNATIVES = 3
# Long enough for two sentences; a paragraph is a sign the model is padding.
MAX_TEXT = 400


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
