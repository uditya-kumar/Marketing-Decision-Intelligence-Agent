"""FR-13.2: scoring a ranked list of causes against the one that was injected."""

from __future__ import annotations

from tests.builders import event

from mdia_eval import diagnosis


def case(*causes: str, kind: str = "creative_fatigue", action: str | None = None) -> diagnosis.Case:
    return diagnosis.Case(
        event_id="ev-1",
        kind=kind,
        causes=tuple(causes),  # type: ignore[arg-type]
        action=action,  # type: ignore[arg-type]
        expected_action="rotate_creative",
        source="llm",
    )


def test_the_cause_ranked_first_counts_for_both() -> None:
    scored = case("creative_fatigue", "cpc_spike")

    assert scored.top1
    assert scored.top3


def test_the_cause_ranked_third_counts_for_the_top_three_only() -> None:
    scored = case("cpc_spike", "conversion_drop", "creative_fatigue")

    assert not scored.top1
    assert scored.top3


def test_a_fourth_place_cause_is_a_miss() -> None:
    scored = case("cpc_spike", "conversion_drop", "unknown", "creative_fatigue")

    assert not scored.top3


def test_an_action_is_only_judged_when_ground_truth_expects_one() -> None:
    assert case(action="rotate_creative").action_right
    assert case(action="shift_budget").action_right is False


def test_accuracy_is_averaged_over_cases_and_split_by_scenario() -> None:
    result = diagnosis.DiagnosisScore(
        source="rules",
        cases=[
            case("creative_fatigue"),
            case("conversion_drop"),
            case("cpc_spike", kind="cpc_spike"),
        ],
    )

    assert result.top1 == 2 / 3
    assert result.by_kind() == {"cpc_spike": (1, 1, 1), "creative_fatigue": (1, 1, 2)}
    assert [miss.kind for miss in result.missed] == ["creative_fatigue"]


def test_the_generators_action_names_are_translated_to_the_catalogue() -> None:
    assert diagnosis.expected_action(event(expected_action="budget_shift")) == "shift_budget"
    assert diagnosis.expected_action(event(expected_action="pause_creative")) == "pause_creative"
    assert diagnosis.expected_action(event()) is None
