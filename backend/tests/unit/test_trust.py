"""Data trust: as-of date, freshness, tracking checks and gating."""

from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd
import pytest

from mdia.domain.periods import Period, trailing
from mdia.domain.trust import (
    Freshness,
    TrackingCheck,
    as_of_date,
    assess_source,
    check_freshness,
    check_tracking,
    missing_sources,
    unreliable_metrics,
    worst,
)

pytestmark = pytest.mark.unit

D = dt.date


def test_as_of_is_the_earliest_latest_date_across_sources() -> None:
    latest = {
        "google_ads": D(2026, 10, 14),
        "meta_ads": D(2026, 10, 14),
        "web_analytics": D(2026, 10, 13),
        "store_orders": D(2026, 10, 14),
    }

    assert as_of_date(latest) == D(2026, 10, 13)
    assert missing_sources(latest) == []


def test_as_of_is_unknown_until_every_source_has_data() -> None:
    latest = {"google_ads": D(2026, 10, 14), "store_orders": None}

    assert as_of_date(latest) is None
    assert missing_sources(latest) == ["meta_ads", "web_analytics", "store_orders"]


# --- freshness ---


def test_fresh_source_with_every_day_is_ok() -> None:
    days = set(trailing(D(2026, 10, 14), 40).dates())

    fresh = check_freshness(days, D(2026, 9, 5), D(2026, 10, 14), newest=D(2026, 10, 14))

    assert fresh == Freshness(D(2026, 10, 14), 0, [])
    assert fresh.status == "ok"


def test_a_source_behind_the_others_is_a_warning() -> None:
    days = set(Period(D(2026, 9, 1), D(2026, 10, 7)).dates())

    fresh = check_freshness(days, D(2026, 9, 1), D(2026, 10, 7), newest=D(2026, 10, 14))

    assert fresh.days_behind == 7
    assert fresh.status == "warning"


def test_gaps_are_reported_only_inside_the_recent_window() -> None:
    days = set(Period(D(2026, 8, 1), D(2026, 10, 14)).dates())
    days -= {D(2026, 8, 20), D(2026, 10, 3), D(2026, 10, 4)}

    fresh = check_freshness(days, D(2026, 8, 1), D(2026, 10, 14), newest=D(2026, 10, 14))

    assert fresh.missing_dates == [D(2026, 10, 3), D(2026, 10, 4)]
    assert fresh.status == "warning"


def test_days_before_the_first_upload_are_not_gaps() -> None:
    days = set(Period(D(2026, 10, 10), D(2026, 10, 14)).dates())

    fresh = check_freshness(days, D(2026, 10, 10), D(2026, 10, 14), newest=D(2026, 10, 14))

    assert fresh.missing_dates == []


def test_a_source_with_no_data_is_broken() -> None:
    fresh = check_freshness(set(), None, None, newest=D(2026, 10, 14))

    assert fresh.last_date is None
    assert fresh.status == "broken"


# --- tracking ---

AS_OF = D(2026, 10, 30)


def _channel(
    break_from: dt.date | None = None, capture: float = 0.15, seed: int = 1
) -> tuple[pd.Series, pd.Series]:
    """60 days of noisy store orders and the platform conversions that follow them."""
    rng = np.random.default_rng(seed)
    dates = trailing(AS_OF, 60).dates()
    orders = pd.Series(rng.normal(200, 20, len(dates)).round(), index=dates)
    conversions = orders * 0.4 * rng.normal(1, 0.08, len(dates))
    if break_from is not None:
        conversions[[day >= break_from for day in dates]] *= capture
    return conversions, orders


def test_steady_tracking_is_ok() -> None:
    conversions, orders = _channel()

    check = check_tracking(conversions, orders, AS_OF)

    assert check is not None
    assert check.status == "ok"
    assert check.since is None
    assert check.ratio_change == pytest.approx(1, abs=0.15)


@pytest.mark.parametrize("seed", range(20))
def test_noise_alone_is_never_flagged(seed: int) -> None:
    conversions, orders = _channel(seed=seed)

    check = check_tracking(conversions, orders, AS_OF)

    assert check is not None
    assert check.status == "ok"


def test_a_broken_pixel_is_flagged_with_the_day_it_started() -> None:
    conversions, orders = _channel(break_from=D(2026, 10, 28))

    check = check_tracking(conversions, orders, AS_OF)

    assert check is not None
    assert check.status == "broken"
    assert check.since == D(2026, 10, 28)
    assert check.conversions_change_pct is not None
    assert check.conversions_change_pct < -70
    assert check.orders_change_pct == pytest.approx(0, abs=10)


def test_a_partial_drop_is_a_warning() -> None:
    conversions, orders = _channel(break_from=D(2026, 10, 28), capture=0.55)

    check = check_tracking(conversions, orders, AS_OF)

    assert check is not None
    assert check.status == "warning"


def test_a_real_sales_slump_is_not_a_tracking_problem() -> None:
    conversions, orders = _channel()
    slump = [day >= D(2026, 10, 28) for day in orders.index]
    orders[slump] *= 0.5
    conversions[slump] *= 0.5

    check = check_tracking(conversions, orders, AS_OF)

    assert check is not None
    assert check.status == "ok"


def test_tracking_needs_enough_history() -> None:
    conversions, orders = _channel()
    recent = trailing(AS_OF, 10).dates()

    assert check_tracking(conversions[recent], orders[recent], AS_OF) is None


def test_tracking_needs_enough_recent_orders() -> None:
    conversions, orders = _channel()
    orders[trailing(AS_OF, 3).dates()] = 5

    assert check_tracking(conversions, orders, AS_OF) is None


# --- status and gating ---

FRESH = Freshness(D(2026, 10, 30), 0, [])
BROKEN = TrackingCheck("broken", 0.15, D(2026, 10, 28), -85.0, 1.0)
WARNING = TrackingCheck("warning", 0.55, D(2026, 10, 28), -45.0, 1.0)


def test_a_source_takes_its_worst_status() -> None:
    assert assess_source("meta_ads", FRESH).status == "ok"
    assert assess_source("meta_ads", FRESH, BROKEN).status == "broken"
    assert worst(["ok", "warning", "ok"]) == "warning"
    assert worst([]) == "ok"


def test_only_broken_tracking_makes_platform_metrics_unreliable() -> None:
    assert unreliable_metrics([assess_source("google_ads", FRESH)]) == set()
    assert unreliable_metrics([assess_source("meta_ads", FRESH, WARNING)]) == set()
    assert unreliable_metrics([assess_source("meta_ads", FRESH, BROKEN)]) == {"roas", "cpa"}
