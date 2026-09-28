"""The action catalogue, the computed confidence and the protected-campaign guardrail."""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from mdia.domain.diagnosis import diagnose
from mdia.domain.evidence import build_evidence
from mdia.domain.recommendations import (
    ACTIONS,
    HALTING,
    MIN_CONFIDENCE,
    Action,
    allowed,
    choose,
    confidence,
    confidence_of,
    priority,
    recommend,
    valid,
)
from tests.builders import SCENARIOS, creative_fatigue, landing_page_break, tracking_break

pytestmark = pytest.mark.unit

UNIT = st.floats(min_value=0.0, max_value=1.0, allow_nan=False)
TERMS = ("strength", "agreement", "share", "trust")


class TestConfidence:
    @given(strength=UNIT, agreement=UNIT, share=UNIT, trust=UNIT)
    def test_it_stays_between_the_floor_and_one(
        self, strength: float, agreement: float, share: float, trust: float
    ) -> None:
        value = confidence(strength=strength, agreement=agreement, share=share, trust=trust)

        assert MIN_CONFIDENCE <= value <= 1.0

    @pytest.mark.parametrize("term", TERMS)
    @given(base=UNIT, step=st.floats(min_value=0.0, max_value=1.0, allow_nan=False))
    def test_it_is_monotonic_in_every_term(self, term: str, base: float, step: float) -> None:
        terms = dict.fromkeys(TERMS, base)
        raised = terms | {term: min(1.0, base + step)}

        assert confidence(**raised) >= confidence(**terms)  # type: ignore[arg-type]

    def test_suspect_data_costs_confidence(self) -> None:
        opportunity = creative_fatigue()

        trusted = confidence_of(build_evidence(opportunity))
        doubted = confidence_of(build_evidence(opportunity, trust="broken"))

        assert doubted < trusted


class TestGuardrail:
    @pytest.mark.parametrize("scenario", sorted(SCENARIOS))
    def test_a_protected_campaign_is_never_told_to_pause(self, scenario: str) -> None:
        evidence = build_evidence(SCENARIOS[scenario](), protected=["7"])

        result = recommend(diagnose(evidence), evidence)

        assert result is None or result.action not in HALTING

    def test_pausing_is_the_rules_choice_without_the_guardrail(self) -> None:
        # Not the first choice, but allowed: the guardrail is what removes it.
        evidence = build_evidence(creative_fatigue())

        assert allowed("pause_creative", evidence) is True
        assert (
            allowed("pause_creative", build_evidence(creative_fatigue(), protected=["7"])) is False
        )

    def test_an_action_the_entity_cannot_take_is_not_allowed(self) -> None:
        evidence = build_evidence(creative_fatigue())

        # A creative has no pacing of its own; that is a channel-level change.
        assert allowed("adjust_pacing", evidence) is False


class TestRecommend:
    @pytest.mark.parametrize("scenario", sorted(SCENARIOS))
    def test_every_scenario_gets_an_action_from_the_catalogue(self, scenario: str) -> None:
        evidence = build_evidence(SCENARIOS[scenario]())

        result = recommend(diagnose(evidence), evidence)

        assert result is not None
        assert result.action in ACTIONS
        assert valid(result.action, result.params)

    def test_the_impact_range_and_priority_are_computed(self) -> None:
        evidence = build_evidence(landing_page_break())

        result = recommend(diagnose(evidence), evidence)

        assert result is not None
        low, high = result.expected_impact
        assert 0 < low < high <= evidence.impact
        assert priority(evidence.impact, result.confidence) == pytest.approx(
            evidence.impact * result.confidence
        )

    def test_a_broken_pixel_is_fixed_before_anything_is_changed(self) -> None:
        evidence = build_evidence(tracking_break(), trust="broken")

        result = recommend(diagnose(evidence), evidence)

        assert result is not None
        assert result.action == "fix_tracking"
        assert result.params["channel"] == "meta_ads"

    def test_an_action_the_llm_may_not_take_is_replaced_by_the_rules_choice(self) -> None:
        evidence = build_evidence(creative_fatigue(), protected=["7"])
        diagnosis = diagnose(evidence)

        result = recommend(diagnosis, evidence, action="pause_creative", rationale="because")

        assert result is not None
        assert result.action == choose(diagnosis, evidence)
        assert result.rationale != "because"

    def test_a_grounded_llm_choice_is_kept_with_its_own_words(self) -> None:
        evidence = build_evidence(creative_fatigue())
        chosen: Action = "rotate_creative"

        result = recommend(diagnose(evidence), evidence, action=chosen, rationale="its own words")

        assert result is not None
        assert (result.action, result.rationale) == (chosen, "its own words")
