"""The investigation graph, run against the fake model: never a wrong number, never a stall."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from mdia.agents.investigation import MAX_RETRIES, build_investigation, investigate
from mdia.agents.schemas import LlmDiagnosis, LlmHypothesis
from mdia.core.settings import get_settings
from tests.builders import creative_fatigue
from tests.fakes import FakeChatModel

if TYPE_CHECKING:
    from mdia.domain.recommendations import Action

pytestmark = pytest.mark.unit

TRUTH = LlmDiagnosis(
    observation="The creative's CPA rose 67% over the 7 days to 28 Oct.",
    hypotheses=[
        LlmHypothesis(
            cause="creative_fatigue",
            statement="CTR fell 40% while CPM held, which is what a tired creative looks like.",
            evidence_signal_ids=["chg|creative:42|ctr|20261028"],
        )
    ],
    alternative_explanations=["The move may not hold next week."],
    action_type="rotate_creative",
    action_rationale="A fresh creative to the same audience is the cheapest test.",
)

LIE = LlmDiagnosis(
    observation="CPA rose to ₹2,450 a sale.",
    hypotheses=[
        LlmHypothesis(
            cause="creative_fatigue",
            statement="CTR fell 82% on this creative.",
            evidence_signal_ids=["chg|creative:99|ctr|20261028"],
        )
    ],
    alternative_explanations=[],
    action_type="rotate_creative",
    action_rationale="It should recover ₹8.2 lakh.",
)


@pytest.fixture(autouse=True)
def _settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """Settings without a ``.env``: nothing here talks to a database or a provider."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://unit/test")
    monkeypatch.setenv("LLM_MODEL", "fake-model")
    get_settings.cache_clear()


class TestGroundedAnswer:
    def test_a_truthful_answer_is_used_and_labelled_llm(self) -> None:
        model = FakeChatModel(answers=[TRUTH])

        result = investigate(build_investigation(model), creative_fatigue())

        assert result.source == "llm"
        assert result.diagnosis.observation == TRUTH.observation
        assert result.diagnosis.hypotheses[0].cause == "creative_fatigue"

    def test_the_numbers_around_it_are_still_computed(self) -> None:
        model = FakeChatModel(answers=[TRUTH])
        opportunity = creative_fatigue()

        result = investigate(build_investigation(model), opportunity)

        assert result.recommendation is not None
        assert result.recommendation.action == TRUTH.action_type
        assert result.recommendation.confidence == result.confidence
        assert result.priority == pytest.approx(opportunity.impact * result.confidence)

    def test_the_call_is_logged_as_grounded(self) -> None:
        model = FakeChatModel(answers=[TRUTH])

        result = investigate(build_investigation(model), creative_fatigue())

        assert len(result.calls) == 1
        record = result.calls[0]
        assert (record.purpose, record.attempt, record.grounded) == ("diagnosis", 1, True)
        assert record.input_tokens and record.output_tokens
        assert record.fallback is False


class TestFallback:
    def test_a_lying_model_ends_in_the_rules(self) -> None:
        model = FakeChatModel(answers=[LIE])

        result = investigate(build_investigation(model), creative_fatigue())

        assert result.source == "rules"
        # The rules' own words, not the model's fabricated ones.
        assert "2,450" not in result.diagnosis.observation
        assert result.diagnosis.hypotheses[0].cause == "creative_fatigue"

    def test_it_is_told_what_was_wrong_and_retried_twice(self) -> None:
        model = FakeChatModel(answers=[LIE])

        result = investigate(build_investigation(model), creative_fatigue())

        assert len(model.prompts) == MAX_RETRIES + 1
        assert "previous answer was rejected" in model.prompts[-1]
        assert [record.attempt for record in result.calls] == [1, 2, 3]
        assert not any(record.grounded for record in result.calls)
        assert result.calls[-1].fallback is True

    def test_an_answer_that_does_not_match_the_schema_falls_back(self) -> None:
        model = FakeChatModel(answers=[None])

        result = investigate(build_investigation(model), creative_fatigue())

        assert result.source == "rules"
        assert result.calls[-1].error

    def test_a_failing_provider_does_not_stop_the_analysis(self) -> None:
        result = investigate(build_investigation(FakeChatModel(raises=True)), creative_fatigue())

        assert result.source == "rules"
        assert result.recommendation is not None
        assert result.calls[-1].fallback is True
        assert "throttled" in (result.calls[-1].error or "")

    def test_without_a_model_the_rules_answer_on_their_own(self) -> None:
        result = investigate(build_investigation(None), creative_fatigue())

        assert (result.source, result.calls) == ("rules", ())
        assert result.recommendation is not None


class TestGuardrails:
    def test_an_action_the_model_may_not_take_is_replaced(self) -> None:
        pausing: Action = "pause_creative"
        answer = TRUTH.model_copy(update={"action_type": pausing})
        model = FakeChatModel(answers=[answer])

        result = investigate(build_investigation(model), creative_fatigue(), protected=["7"])

        # Grounding rejects the action, so the whole answer goes to the rules (FR-9.4).
        assert result.source == "rules"
        assert result.recommendation is not None
        assert result.recommendation.action != pausing
