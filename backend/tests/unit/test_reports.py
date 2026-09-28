"""The weekly report's payload and its fallback prose (FR-11.1, FR-11.2)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from mdia.agents.grounding import matches, numbers_in
from mdia.domain.report_text import template
from mdia.domain.reports import MAX_DECISIONS, TOP_OPPORTUNITIES, quotable
from tests.report_builders import (
    report_decision,
    report_experiment,
    report_kpi,
    report_opportunity,
    report_pacing,
    weekly_payload,
)

if TYPE_CHECKING:
    from mdia.domain.reports import WeeklyPayload

pytestmark = pytest.mark.unit


class TestBuild:
    def test_it_totals_the_week_by_kind(self) -> None:
        week = weekly_payload()
        assert week.issue_cost == 84_000.0
        assert week.win_upside == 36_000.0
        assert week.worked == 1

    def test_impact_counts_towards_the_total_whichever_sign_it_carries(self) -> None:
        week = weekly_payload(opportunities=[report_opportunity(impact=-84_000.0)])
        assert week.issue_cost == 84_000.0

    def test_it_keeps_only_the_rows_worth_printing(self) -> None:
        many = [report_opportunity(index) for index in range(TOP_OPPORTUNITIES + 3)]
        week = weekly_payload(
            opportunities=many, decisions=[report_decision()] * (MAX_DECISIONS + 2)
        )
        assert len(week.opportunities) == TOP_OPPORTUNITIES
        assert len(week.decisions) == MAX_DECISIONS

    def test_the_totals_still_cover_the_rows_it_dropped(self) -> None:
        week = weekly_payload(
            opportunities=[report_opportunity(index) for index in range(TOP_OPPORTUNITIES + 3)]
        )
        assert week.issue_cost == 84_000.0 * (TOP_OPPORTUNITIES + 3)

    def test_issues_come_before_wins(self) -> None:
        week = weekly_payload(
            opportunities=[report_opportunity(1, "win"), report_opportunity(2, "issue")]
        )
        assert [row.kind for row in week.opportunities] == ["issue", "win"]

    def test_one_unreliable_kpi_warns_the_whole_report(self) -> None:
        assert weekly_payload().trust_warning is False
        assert (
            weekly_payload(
                kpis=[report_kpi(), report_kpi("cvr", 0.0181, reliable=False)]
            ).trust_warning
            is True
        )


class TestQuotable:
    def test_a_value_counts_as_the_reader_sees_it(self) -> None:
        permitted = quotable(
            weekly_payload(kpis=[report_kpi("cvr", 0.0181, target=None, goal_status=None)])
        )
        assert matches(1.81, permitted)

    def test_rupees_count_both_as_written_and_in_lakhs(self) -> None:
        permitted = quotable(weekly_payload())
        assert matches(1_640_000, permitted)
        assert matches(16.40, permitted)

    def test_counting_its_own_rows_is_allowed(self) -> None:
        permitted = quotable(
            weekly_payload(experiments=[report_experiment(), report_experiment(None)])
        )
        assert matches(2, permitted)

    def test_a_number_from_no_row_at_all_is_not(self) -> None:
        assert not matches(913.0, quotable(weekly_payload()))


class TestTemplate:
    def test_it_leads_on_revenue_and_the_week(self) -> None:
        text = template(weekly_payload())
        assert (
            text.summary[0]
            == "Revenue was ₹16.40 L in the 7 days to 22 Oct 2026, fell 21% on the week before."
        )

    def test_it_names_the_goals_that_were_missed(self) -> None:
        assert "Behind goal: store revenue ₹16.40 L." in template(weekly_payload()).summary

    def test_with_every_goal_met_it_says_so_rather_than_nothing(self) -> None:
        text = template(weekly_payload(kpis=[report_kpi(goal_status="on_track")]))
        assert "Every goal with a target was met or on track." in text.summary

    def test_it_closes_on_what_was_decided_and_how_it_turned_out(self) -> None:
        assert (
            template(weekly_payload()).summary[-1] == "1 decision recorded; of 1 judged, 1 worked."
        )

    def test_without_a_verdict_it_does_not_claim_one(self) -> None:
        text = template(weekly_payload(experiments=[report_experiment(None)]))
        assert text.summary[-1] == "1 decision recorded, none judged yet."

    def test_a_quiet_week_still_reads_as_a_report(self) -> None:
        text = template(weekly_payload(opportunities=[], decisions=[], experiments=[]))
        assert text.summary[-1] == "No decisions were recorded this week."
        assert all(line for line in text.detail)

    def test_the_detail_carries_a_section_per_kind_of_row(self) -> None:
        detail = template(weekly_payload()).detail
        assert [line.split(".")[0] for line in detail] == [
            "This week's KPIs",
            "Budget pacing",
            "What mattered",
            "Changes under test",
            "Decisions",
        ]

    def test_an_empty_section_is_left_out_rather_than_left_blank(self) -> None:
        detail = template(weekly_payload(pacing=[], experiments=[])).detail
        assert not any(line.startswith("Budget pacing") for line in detail)

    def test_an_unreliable_kpi_is_flagged_where_it_is_read(self) -> None:
        detail = template(weekly_payload(kpis=[report_kpi(reliable=False)])).detail
        assert "not reliable while tracking is broken" in detail[0]

    def test_a_missing_value_reads_as_missing_instead_of_zero(self) -> None:
        detail = template(weekly_payload(kpis=[report_kpi(value=None, change_pct=None)])).detail
        assert "Store revenue n/a" in detail[0]


class TestTheTemplateIsGrounded:
    """The fallback is the floor for FR-11.2: it may only print the payload's own numbers."""

    @pytest.mark.parametrize(
        "week",
        [
            weekly_payload(),
            weekly_payload(kpis=[report_kpi("cvr", 0.0181, previous=0.0242, target=0.02)]),
            weekly_payload(
                experiments=[report_experiment(None), report_experiment("did_not_work")]
            ),
            weekly_payload(opportunities=[], decisions=[], experiments=[]),
            weekly_payload(pacing=[report_pacing(spent=90_000.0)]),
        ],
    )
    def test_every_number_it_prints_is_in_the_weekly_payload(self, week: WeeklyPayload) -> None:
        permitted = quotable(week)
        text = template(week)
        for line in [*text.summary, *text.detail]:
            for value in numbers_in(line):
                assert matches(value, permitted), f"{value:g} is not in the payload: {line}"
