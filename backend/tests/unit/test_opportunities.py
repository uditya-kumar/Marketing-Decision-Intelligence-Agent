"""Grouping signals into one thing to act on, with a key that survives a re-run."""

from __future__ import annotations

import datetime as dt

import pytest

from mdia.domain.opportunities import first_seen, group, most_specific
from mdia.domain.periods import trailing
from mdia.domain.signals import WINDOW_DAYS, Entity, Signal, signal_id

pytestmark = pytest.mark.unit

AS_OF = dt.date(2026, 10, 28)
RECENT = trailing(AS_OF, WINDOW_DAYS)

CHANNEL = Entity("channel", "meta_ads", "Meta Ads", "meta_ads", ("account:all",))
OTHER_CHANNEL = Entity("channel", "google_ads", "Google Ads", "google_ads", ("account:all",))
CAMPAIGN = Entity(
    "campaign", "7", "NW | IG | Reels", "meta_ads", ("account:all", "channel:meta_ads")
)
OTHER_CAMPAIGN = Entity(
    "campaign", "8", "NW | FB | Retargeting", "meta_ads", ("account:all", "channel:meta_ads")
)
CREATIVE = Entity(
    "creative",
    "42",
    "Reel | Get Ready With Me",
    "meta_ads",
    ("account:all", "channel:meta_ads", "campaign:7"),
)


def signal(entity: Entity, metric: str, *, adverse: bool = True, score: float = 10_000.0) -> Signal:
    return Signal(
        id=signal_id("baseline_change", entity, metric, RECENT),  # type: ignore[arg-type]
        detector="baseline_change",
        metric=metric,  # type: ignore[arg-type]
        entity=entity,
        window=RECENT,
        current=600,
        baseline=400,
        change_pct=50 if adverse else -50,
        adverse=adverse,
        impact=score * 2,
        score=score,
    )


class TestMostSpecific:
    def test_the_parent_saying_the_same_thing_is_dropped(self) -> None:
        kept = most_specific(
            [signal(CHANNEL, "cpa"), signal(CAMPAIGN, "cpa"), signal(CREATIVE, "cpa")]
        )

        assert [s.entity.level for s in kept] == ["creative"]

    def test_a_different_metric_on_the_parent_stays(self) -> None:
        kept = most_specific([signal(CHANNEL, "roas"), signal(CREATIVE, "cpa")])

        assert {s.entity.level for s in kept} == {"channel", "creative"}

    def test_a_parent_moving_the_other_way_stays(self) -> None:
        kept = most_specific([signal(CHANNEL, "cpa", adverse=False), signal(CREATIVE, "cpa")])

        assert len(kept) == 2

    def test_a_movement_across_the_children_belongs_to_the_parent(self) -> None:
        # Both of the channel's campaigns moved, so it is the channel that moved.
        kept = most_specific(
            [signal(CHANNEL, "cpc"), signal(CAMPAIGN, "cpc"), signal(OTHER_CAMPAIGN, "cpc")],
            children={"channel:meta_ads": 2},
        )

        assert [s.entity.level for s in kept] == ["channel"]

    def test_a_broad_movement_no_parent_reported_stays_where_it_is(self) -> None:
        # Every channel is over its own budget, but the account has no budget of its own:
        # rolling the finding up to it would leave nothing to show.
        kept = most_specific(
            [signal(CHANNEL, "spend"), signal(OTHER_CHANNEL, "spend")],
            children={"account:all": 2},
        )

        assert [s.entity.key for s in kept] == ["meta_ads", "google_ads"]


class TestGroup:
    def test_one_scenario_becomes_one_opportunity(self) -> None:
        # A tired creative moves its own metrics and every level above it.
        found = group(
            [
                signal(CREATIVE, "ctr", score=8_000),
                signal(CREATIVE, "cpa", score=30_000),
                signal(CAMPAIGN, "cpa", score=30_000),
                signal(CHANNEL, "cpa", score=30_000),
            ]
        )

        assert len(found) == 1
        opportunity = found[0]
        assert opportunity.key == "creative:42"
        assert opportunity.kind == "issue"
        assert opportunity.primary_metric == "cpa"
        assert [s.metric for s in opportunity.signals] == ["cpa", "ctr"]
        # The same rupees twice would double-count the problem.
        assert opportunity.impact == pytest.approx(60_000)
        assert opportunity.score == pytest.approx(30_000)

    def test_a_win_is_an_opportunity_too(self) -> None:
        found = group([signal(CHANNEL, "roas", adverse=False)])

        assert [o.kind for o in found] == ["win"]

    def test_entities_are_ordered_by_score(self) -> None:
        found = group([signal(CHANNEL, "roas", score=5_000), signal(CREATIVE, "cpa", score=9_000)])

        assert [o.key for o in found] == ["creative:42", "channel:meta_ads"]

    def test_the_key_is_stable_across_runs(self) -> None:
        first = group([signal(CREATIVE, "cpa")])
        again = group([signal(CREATIVE, "cpa"), signal(CREATIVE, "ctr")])

        assert first[0].key == again[0].key


class TestFirstSeen:
    def test_a_new_opportunity_starts_with_its_window(self) -> None:
        assert first_seen(RECENT, None) == RECENT.start

    def test_a_continuing_one_keeps_the_original_date(self) -> None:
        earlier = dt.date(2026, 10, 10)

        assert first_seen(RECENT, (earlier, dt.date(2026, 10, 25))) == earlier

    def test_it_restarts_after_a_long_gap(self) -> None:
        assert first_seen(RECENT, (dt.date(2026, 8, 1), dt.date(2026, 9, 1))) == RECENT.start
