"""The evidence tree and the rule-based diagnosis, over the seven scenario shapes."""

from __future__ import annotations

import pytest

from mdia.domain.diagnosis import diagnose
from mdia.domain.evidence import build_evidence, build_tree, dominant_chain, is_protected
from mdia.domain.wording import rupees
from tests.builders import BASELINE, CAMPAIGN, CREATIVE, SCENARIOS, creative_fatigue

pytestmark = pytest.mark.unit


class TestEvidenceTree:
    def test_the_drivers_of_a_cpa_move_are_the_tree(self) -> None:
        after = dict(BASELINE) | {"clicks": 9_000.0, "platform_conversions": 270.0}

        tree = build_tree("cpa", BASELINE, after)

        assert tree.metric == "cpa"
        assert [child.metric for child in tree.children] == ["cpc", "cvr"]
        # CTR carried CPC, and CPC carried CPA: 100 % of the move, twice.
        assert [node.metric for node in dominant_chain(tree)] == ["cpc", "ctr"]

    def test_a_metric_with_no_formula_is_a_leaf(self) -> None:
        tree = build_tree("spend", BASELINE, BASELINE)

        assert tree.children == ()

    def test_evidence_carries_what_the_diagnosis_may_use(self) -> None:
        evidence = build_evidence(creative_fatigue(), trust="warning", protected=["7"])

        assert evidence.entity is CREATIVE
        assert evidence.trust == "warning"
        assert evidence.protected is True
        assert len(evidence.signal_ids) == 3


class TestProtected:
    def test_a_campaign_in_the_list_is_protected(self) -> None:
        assert is_protected(CAMPAIGN, ["7"]) is True

    def test_so_is_anything_inside_it(self) -> None:
        assert is_protected(CREATIVE, ["7"]) is True

    def test_and_nothing_else_is(self) -> None:
        assert is_protected(CREATIVE, ["8"]) is False


class TestDiagnose:
    @pytest.mark.parametrize("scenario", sorted(SCENARIOS))
    def test_the_leading_hypothesis_names_the_scenario(self, scenario: str) -> None:
        evidence = build_evidence(SCENARIOS[scenario]())

        diagnosis = diagnose(evidence)

        assert diagnosis.hypotheses[0].cause == scenario

    def test_every_hypothesis_cites_signals_from_the_evidence(self) -> None:
        evidence = build_evidence(creative_fatigue())

        diagnosis = diagnose(evidence)

        assert diagnosis.hypotheses
        for hypothesis in diagnosis.hypotheses:
            assert hypothesis.signal_ids
            assert set(hypothesis.signal_ids) <= set(evidence.signal_ids)

    def test_the_observation_is_one_sentence_of_computed_numbers(self) -> None:
        evidence = build_evidence(creative_fatigue())

        text = diagnose(evidence).observation

        assert CREATIVE.name in text
        assert "CPA rose 67%" in text

    def test_suspect_data_is_always_offered_as_an_alternative(self) -> None:
        evidence = build_evidence(creative_fatigue(), trust="broken")

        assert any("reporting problem" in text for text in diagnose(evidence).alternatives)


class TestRupees:
    @pytest.mark.parametrize(
        ("value", "text"),
        [(9_500.0, "₹9,500"), (340_000.0, "₹3.40 L"), (25_000_000.0, "₹2.50 Cr")],
    )
    def test_money_reads_in_indian_units(self, value: float, text: str) -> None:
        assert rupees(value) == text
