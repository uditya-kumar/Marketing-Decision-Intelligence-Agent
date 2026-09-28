"""FR-13.4: the rate before the guard counts attempts, the rate after counts answers."""

from __future__ import annotations

from tests.builders import call

from mdia_eval import grounding


def test_a_retry_that_succeeds_is_a_violation_before_the_guard_only() -> None:
    result = grounding.score([call(attempt=1, grounded=False), call(attempt=2, grounded=True)])

    assert result.answers == 1
    assert result.violation_rate == 0.5
    assert result.fallback_rate == 0.0
    assert result.recovered == 1
    assert result.leaked == 0


def test_an_answer_that_never_grounds_ends_rule_based() -> None:
    calls = [
        call(attempt=1, grounded=False, fallback=True),
        call(attempt=2, grounded=False, fallback=True),
    ]

    result = grounding.score(calls)

    assert result.fell_back == 1
    assert result.fallback_rate == 1.0
    assert result.violation_rate == 1.0


def test_a_transport_failure_is_not_counted_as_a_violation() -> None:
    result = grounding.score([call(attempt=1, grounded=False, fallback=True, error="timeout")])

    assert result.errors == 1
    assert result.ungrounded == 0
    assert result.fallback_rate == 1.0


def test_purposes_are_scored_apart() -> None:
    calls = [
        call(purpose="diagnosis", grounded=False, fallback=True),
        call(purpose="report"),
    ]

    parts = grounding.score(calls).by_purpose()

    assert parts["diagnosis"].fallback_rate == 1.0
    assert parts["report"].fallback_rate == 0.0


def test_nothing_logged_scores_zero_rather_than_dividing_by_zero() -> None:
    result = grounding.score([])

    assert result.violation_rate == 0.0
    assert result.fallback_rate == 0.0
