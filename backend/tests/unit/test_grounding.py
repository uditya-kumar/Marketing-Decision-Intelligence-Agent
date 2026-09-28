"""The grounding guard: an answer may only contain what the evidence gave it."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from mdia.agents.grounding import allowed_numbers, check, numbers_in
from mdia.agents.schemas import LlmDiagnosis, LlmHypothesis
from mdia.domain.diagnosis import Evidence, build_evidence
from tests.builders import creative_fatigue

if TYPE_CHECKING:
    from mdia.domain.recommendations import Action

pytestmark = pytest.mark.unit


@pytest.fixture
def evidence() -> Evidence:
    return build_evidence(creative_fatigue())


def answer(
    evidence: Evidence,
    *,
    statement: str = "CTR fell 40% and took CPC with it.",
    observation: str = "CPA rose 67% over the 7 days to 28 Oct.",
    rationale: str = "A fresh creative to the same audience tests that.",
    signal_ids: list[str] | None = None,
    action: Action = "rotate_creative",
) -> LlmDiagnosis:
    return LlmDiagnosis(
        observation=observation,
        hypotheses=[
            LlmHypothesis(
                cause="creative_fatigue",
                statement=statement,
                evidence_signal_ids=(
                    signal_ids if signal_ids is not None else [evidence.signal_ids[0]]
                ),
            )
        ],
        alternative_explanations=["Normal week-to-week variation."],
        action_type=action,
        action_rationale=rationale,
    )


class TestCheck:
    def test_an_answer_that_only_quotes_the_evidence_passes(self, evidence: Evidence) -> None:
        assert check(answer(evidence), evidence) == []

    def test_a_fabricated_signal_id_is_caught(self, evidence: Evidence) -> None:
        invented = "chg|creative:99|cpa|20261028"

        violations = check(answer(evidence, signal_ids=[invented]), evidence)

        assert any(invented in violation for violation in violations)

    def test_a_fabricated_number_is_caught(self, evidence: Evidence) -> None:
        violations = check(answer(evidence, statement="CPA is now ₹2,450 a sale."), evidence)

        assert any("2450" in violation for violation in violations)

    def test_a_fabricated_number_in_the_rationale_is_caught_too(self, evidence: Evidence) -> None:
        violations = check(answer(evidence, rationale="It should recover ₹7.7 lakh."), evidence)

        assert any("action rationale" in violation for violation in violations)

    def test_an_action_this_entity_cannot_take_is_caught(self, evidence: Evidence) -> None:
        violations = check(answer(evidence, action="adjust_pacing"), evidence)

        assert any("adjust_pacing" in violation for violation in violations)

    def test_pausing_a_protected_campaign_is_caught(self) -> None:
        evidence = build_evidence(creative_fatigue(), protected=["7"])

        violations = check(answer(evidence, action="pause_creative"), evidence)

        assert any("protected" in violation for violation in violations)

    def test_a_rounded_number_still_counts_as_quoted(self, evidence: Evidence) -> None:
        # CPA is ₹1,111.11; a model writing ₹1,111 has not invented anything.
        assert check(answer(evidence, statement="CPA is ₹1,111 a sale."), evidence) == []


class TestNumbers:
    def test_a_rate_counts_as_the_percentage_it_is_shown_as(self, evidence: Evidence) -> None:
        permitted = allowed_numbers(evidence)

        assert any(abs(value - 0.9) < 0.01 for value in permitted)
        assert 0.009 in permitted

    def test_signal_ids_are_not_read_as_numbers(self, evidence: Evidence) -> None:
        text = f"See {evidence.signal_ids[0]} for the move."

        assert numbers_in(text, ignore=evidence.signal_ids) == []

    def test_indian_units_are_read_both_ways(self) -> None:
        assert numbers_in("₹3.40 L at stake") == [340_000.0, 3.4]
