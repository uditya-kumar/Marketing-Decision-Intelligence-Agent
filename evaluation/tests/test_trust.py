"""FR-13.3: a break is only scored as handled when it was caught and advice stopped."""

from __future__ import annotations

from typing import TYPE_CHECKING

from tests.builders import check, day, event, opportunity, run, signal

from mdia_eval import trust

if TYPE_CHECKING:
    from mdia.domain.trust import TrustStatus

    from mdia_eval.replay import Run


def _runs(broken_from: int | None, *, advice: bool = False) -> list[Run]:
    runs = []
    for offset in range(5):
        status: TrustStatus = (
            "broken" if broken_from is not None and offset >= broken_from else "ok"
        )
        shown = (opportunity(signal("roas")),) if advice and status == "broken" else ()
        runs.append(run(day(offset), opportunities=shown, tracking={"meta_ads": check(status)}))
    return runs


def test_a_break_called_on_its_second_day_is_caught_with_a_lag() -> None:
    result = trust.score(_runs(broken_from=1), [event()])

    assert result.accuracy == 1.0
    assert result.suppression == 1.0
    assert result.breaks[0].lag_days == 1
    assert result.breaks[0].caught_days == 4


def test_a_break_never_called_is_missed() -> None:
    result = trust.score(_runs(broken_from=None), [event()])

    assert result.accuracy == 0.0
    assert result.missed[0].event_id == "ev-tracking_break"


def test_platform_based_advice_on_a_broken_day_is_a_leak() -> None:
    result = trust.score(_runs(broken_from=0, advice=True), [event()])

    assert result.accuracy == 1.0
    assert result.suppression == 0.0
    assert result.leaked[0].leaked == ("campaign:c1",)


def test_store_based_advice_survives_a_broken_pixel() -> None:
    runs = [
        run(
            day(offset),
            opportunities=(opportunity(signal("store_roas")),),
            tracking={"meta_ads": check("broken")},
        )
        for offset in range(5)
    ]

    result = trust.score(runs, [event()])

    assert result.suppression == 1.0


def test_broken_days_outside_every_window_are_false_alarms() -> None:
    runs = _runs(broken_from=0)
    result = trust.score(runs, [event(start=day(10))])

    assert result.false_days == 5
    assert result.false_alarm_rate == 1.0
    # The window itself was never replayed, so it is reported apart from the misses.
    assert result.uncovered and not result.breaks


def test_scenarios_that_are_not_breaks_are_ignored() -> None:
    result = trust.score(_runs(broken_from=None), [event("cpc_spike")])

    assert result.breaks == []
    assert result.accuracy == 0.0
