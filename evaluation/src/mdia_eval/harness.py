"""Loading a dataset, replaying it and scoring detection: what every command starts with.

Kept apart from the CLI so the four §13 reports share one replay instead of each paying
for their own.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from mdia.domain.scoring import MIN_SCORE

from mdia_eval import detection, facts, settings, truth
from mdia_eval.replay import covered, replay

if TYPE_CHECKING:
    from pathlib import Path

    from mdia_eval.detection import Score
    from mdia_eval.replay import Run
    from mdia_eval.settings import EvalSettings
    from mdia_eval.truth import Event


@dataclass(frozen=True, slots=True)
class Replayed:
    """One dataset, replayed day by day and scored against what was injected."""

    runs: list[Run]
    events: list[Event]
    detected: Score
    business: EvalSettings


def run(
    data: Path,
    world: Path,
    *,
    min_score: float = MIN_SCORE,
    festive: bool = True,
) -> Replayed:
    loaded = facts.load(data)
    business = settings.load(world)
    events = truth.load(data / "ground_truth.json", facts.lineage(loaded.ads))
    runs = replay(loaded, business, festive=festive, min_score=min_score)
    windows = business.festive if festive else ()
    detected = detection.split_suppressed(
        detection.score(detection.episodes(runs), events, covered(runs)), windows
    )
    return Replayed(runs=runs, events=events, detected=detected, business=business)
