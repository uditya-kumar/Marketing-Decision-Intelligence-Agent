"""Numbers becoming words: the sentences every screen and prompt is built from."""

from __future__ import annotations

from mdia.domain.wording import as_shown, moved, rupees, title, value_text


class TestTitle:
    def test_a_known_metric_reads_as_what_it_means_for_the_business(self) -> None:
        assert title("Meta Ads", "cpa", kind="issue") == "Meta Ads costs more per sale"
        assert title("Meta Ads", "cpa", kind="win") == "Meta Ads costs less per sale"

    def test_a_metric_without_a_phrase_falls_back_to_the_direction(self) -> None:
        assert title("All channels", "store_revenue", kind="issue") == (
            "All channels: store revenue moved the wrong way"
        )
        assert title("All channels", "store_revenue", kind="win") == (
            "All channels: store revenue moved the right way"
        )


class TestMoved:
    def test_it_names_the_direction_without_a_sign(self) -> None:
        assert moved(45.4) == "rose 45%"
        assert moved(-45.4) == "fell 45%"

    def test_without_a_baseline_it_only_says_that_it_moved(self) -> None:
        assert moved(None) == "moved"


class TestValueText:
    def test_a_rate_is_shown_as_a_percentage(self) -> None:
        assert value_text("cvr", 0.0406) == "4.06%"

    def test_a_multiple_keeps_its_x(self) -> None:
        assert value_text("roas", 5.1122) == "5.11x"

    def test_a_count_is_not_money(self) -> None:
        assert value_text("store_orders", 1234.6) == "1,235"

    def test_anything_else_is_rupees(self) -> None:
        assert value_text("cpa", 397.2) == "₹397"


def test_as_shown_scales_only_the_rates() -> None:
    assert as_shown("cvr", 0.0406) == 0.0406 * 100
    assert as_shown("roas", 5.11) == 5.11


class TestRupees:
    def test_lakhs_and_crores_are_used_where_an_operator_expects_them(self) -> None:
        assert rupees(1_638_500) == "₹16.39 L"
        assert rupees(27_610_000) == "₹2.76 Cr"

    def test_small_amounts_are_grouped_and_not_abbreviated(self) -> None:
        assert rupees(41_104) == "₹41,104"

    def test_a_negative_amount_is_abbreviated_on_its_size(self) -> None:
        assert rupees(-250_000) == "₹-2.50 L"
