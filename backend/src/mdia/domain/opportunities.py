"""Grouping signals into opportunities (FR-6.4).

One problem shows up as several signals: a tired creative lifts its own CPA, its ad
set's and its channel's, and drags CTR down with it. Grouping turns that back into a
single thing to act on, keyed so that re-running the analysis updates the same row
instead of adding another.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from mdia.domain.signals import WINDOW_DAYS

if TYPE_CHECKING:
    import datetime as dt
    from collections.abc import Iterable, Mapping, Sequence

    from mdia.domain.kpi import Metric
    from mdia.domain.periods import Period
    from mdia.domain.signals import Detector, Entity, Signal

OpportunityKind = Literal["issue", "win"]

# Once this share of an entity's children move the same way, it is the entity that
# moved, not each child in turn.
BROAD_SHARE = 0.5
# A peer comparison says nothing about the parent, so it stays out of the roll-up.
_PEER_DETECTOR: Detector = "segment_divergence"

# One movement, as the roll-up sees it: whose, of what, in which direction.
type _Move = tuple[str, Detector, Metric, bool]


@dataclass(frozen=True, slots=True)
class Opportunity:
    """Everything detected about one entity in one window."""

    # Stable across runs: the same entity keeps the same opportunity row.
    key: str
    kind: OpportunityKind
    entity: Entity
    window: Period
    # The signal that earns the opportunity its place in the list.
    primary: Signal
    signals: tuple[Signal, ...]
    impact: float
    score: float

    @property
    def primary_metric(self) -> Metric:
        return self.primary.metric


def most_specific(
    signals: Iterable[Signal], *, children: Mapping[str, int] | None = None
) -> list[Signal]:
    """Report a movement at the one level where it can be acted on.

    A creative whose CPA doubled also moves its ad set, campaign and channel CPA, and
    only the creative can be rotated — so the parents drop out. When the movement runs
    across most of an entity's children instead, the auction (or the season) moved and
    that entity is the one thing to act on, so this time everything under it drops out.
    ``children`` says how many children each entity has; without it a movement counts as
    broad once two of them share it.
    """
    signals = list(signals)
    rolled = [signal for signal in signals if signal.detector != _PEER_DETECTOR]
    deeper = {_move(signal, ancestor) for signal in rolled for ancestor in signal.entity.ancestors}
    broad = _broad_moves(rolled, children or {})

    def keep(signal: Signal) -> bool:
        if signal.detector == _PEER_DETECTOR:
            return True
        # The highest entity the movement ran across owns it; nothing under it does.
        if any(_move(signal, ancestor) in broad for ancestor in signal.entity.ancestors):
            return False
        own = _move(signal, signal.entity.id)
        return own not in deeper or own in broad

    return [signal for signal in signals if keep(signal)]


def _broad_moves(signals: Sequence[Signal], counts: Mapping[str, int]) -> set[_Move]:
    """Movements that ran across enough of an entity's children to be its own.

    A child counts as carrying the movement when it reported it itself or when the
    movement ran across *its* children in turn — so a level that never checks the
    metric, as ad sets never check CPC, doesn't break the chain. Children are
    therefore resolved deepest first.

    Only an entity that reported the movement itself can take it over: the channel
    whose budget is overspent has no account above it watching the same budget, and
    promoting the finding there would leave nothing to show at all.
    """
    owned = {_move(signal, signal.entity.id) for signal in signals}
    seen: dict[_Move, set[str]] = defaultdict(set)
    depth: dict[str, int] = {}
    for signal in signals:
        chain = (*signal.entity.ancestors, signal.entity.id)
        for index, entity_id in enumerate(chain):
            depth[entity_id] = index
            if index + 1 < len(chain):
                seen[_move(signal, entity_id)].add(chain[index + 1])
    across: set[_Move] = set()
    for move, branches in sorted(seen.items(), key=lambda item: -depth[item[0][0]]):
        carrying = {
            child for child in branches if _at(move, child) in owned or _at(move, child) in across
        }
        if len(carrying) >= 2 and len(carrying) >= BROAD_SHARE * counts.get(move[0], len(branches)):
            across.add(move)
    return across & owned


def group(
    signals: Iterable[Signal], *, children: Mapping[str, int] | None = None
) -> list[Opportunity]:
    """Group signals by entity, strongest first. Expects already-scored signals."""
    by_entity: dict[str, list[Signal]] = defaultdict(list)
    for signal in most_specific(signals, children=children):
        by_entity[signal.entity.id].append(signal)
    found = [_opportunity(key, group) for key, group in by_entity.items()]
    return sorted(found, key=lambda opportunity: opportunity.score, reverse=True)


def _move(signal: Signal, entity_id: str) -> _Move:
    return (entity_id, signal.detector, signal.metric, signal.adverse)


def _at(move: _Move, entity_id: str) -> _Move:
    """The same movement, asked about another entity."""
    return (entity_id, *move[1:])


def _opportunity(key: str, signals: Sequence[Signal]) -> Opportunity:
    ordered = sorted(signals, key=lambda signal: signal.score, reverse=True)
    primary = ordered[0]
    return Opportunity(
        key=key,
        kind="issue" if primary.adverse else "win",
        entity=primary.entity,
        window=primary.window,
        primary=primary,
        signals=tuple(ordered),
        # The max, not the sum: CPA and CTR moving together are the same rupees twice.
        impact=max(signal.impact for signal in ordered),
        score=max(signal.score for signal in ordered),
    )


def first_seen(window: Period, previous: tuple[dt.date, dt.date] | None) -> dt.date:
    """When this opportunity started, given the ``(first, last)`` seen dates of its row.

    A gap longer than one detection window means the problem went away and came
    back, so days-to-detect is measured from the new occurrence.
    """
    if previous is None:
        return window.start
    first, last = previous
    if (window.start - last).days > WINDOW_DAYS:
        return window.start
    return min(first, window.start)
