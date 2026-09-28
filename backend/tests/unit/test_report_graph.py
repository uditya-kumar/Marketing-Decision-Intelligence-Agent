"""The weekly report graph against the fake model: better words, never a new number."""

from __future__ import annotations

import pytest

from mdia.agents.grounding import matches, numbers_in
from mdia.agents.report import MAX_RETRIES, build_report, write_report
from mdia.agents.schemas import LlmReport
from mdia.core.settings import get_settings
from mdia.domain.reports import quotable
from tests.fakes import FakeChatModel
from tests.report_builders import weekly_payload

pytestmark = pytest.mark.unit

TRUTH = LlmReport(
    summary=[
        "Revenue came to ₹16.40 L in the 7 days to 22 Oct 2026, down 21% on the week before.",
        "One issue is costing about ₹84,000 a week.",
        "1 decision was recorded, and it worked.",
    ],
    detail=[
        "KPIs. Store revenue ₹16.40 L against a target of ₹18.70 L, with CPA at ₹612.",
        "Changes under test. The retargeting creative rotation took CPA ₹612 to ₹438 over 7 days.",
    ],
)

LIE = LlmReport(
    summary=["Revenue came to ₹16.40 L, and margin held at 42%."],
    detail=["KPIs. Store revenue ₹16.40 L against a target of ₹18.70 L."],
)


@pytest.fixture(autouse=True)
def _settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """Settings without a ``.env``: nothing here talks to a database or a provider."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://unit/test")
    monkeypatch.setenv("LLM_MODEL", "fake-model")
    get_settings.cache_clear()


class TestGroundedNarrative:
    def test_a_truthful_narrative_is_used_as_written(self) -> None:
        model = FakeChatModel(answers=[TRUTH])

        report = write_report(build_report(model), weekly_payload())

        assert report.source == "llm"
        assert report.grounded is True
        assert report.text.summary == TRUTH.summary
        assert report.text.detail == TRUTH.detail

    def test_the_call_is_logged_as_grounded(self) -> None:
        model = FakeChatModel(answers=[TRUTH])

        report = write_report(build_report(model), weekly_payload())

        assert [(call.purpose, call.attempt, call.grounded) for call in report.calls] == [
            ("report", 1, True)
        ]

    def test_every_number_it_prints_is_in_the_payload(self) -> None:
        payload = weekly_payload()
        report = write_report(build_report(FakeChatModel(answers=[TRUTH])), payload)

        permitted = quotable(payload)
        for line in [*report.text.summary, *report.text.detail]:
            for value in numbers_in(line):
                assert matches(value, permitted), f"{value:g} is not in the payload: {line}"


class TestInventedNumbers:
    def test_a_made_up_number_is_retried_then_dropped_for_the_template(self) -> None:
        model = FakeChatModel(answers=[LIE])

        report = write_report(build_report(model), weekly_payload())

        assert report.source == "template"
        assert report.grounded is False
        assert len(model.prompts) == MAX_RETRIES + 1

    def test_the_retry_is_told_which_number_was_invented(self) -> None:
        model = FakeChatModel(answers=[LIE])

        write_report(build_report(model), weekly_payload())

        assert "42" in model.prompts[1]
        assert "not in the report's facts" in model.prompts[1]

    def test_a_corrected_second_answer_is_accepted(self) -> None:
        model = FakeChatModel(answers=[LIE, TRUTH])

        report = write_report(build_report(model), weekly_payload())

        assert report.source == "llm"
        assert [call.grounded for call in report.calls] == [False, True]


class TestTheReportAlwaysArrives:
    def test_without_a_model_the_template_writes_it(self) -> None:
        report = write_report(build_report(None), weekly_payload())

        assert report.source == "template"
        assert report.calls == ()
        assert report.text.summary[0].startswith("Revenue was ₹16.40 L")

    def test_an_answer_that_does_not_match_the_schema_falls_back(self) -> None:
        report = write_report(build_report(FakeChatModel(answers=[None])), weekly_payload())

        assert report.source == "template"
        assert all(call.fallback for call in report.calls)

    def test_a_provider_failure_falls_back_with_the_error_logged(self) -> None:
        report = write_report(build_report(FakeChatModel(raises=True)), weekly_payload())

        assert report.source == "template"
        assert report.calls[0].error is not None
        assert report.text.detail
