"""The figures the thesis needs, written as PNGs beside the tables.

Three charts, one per claim the evaluation makes: the detectors find scenarios, they
find them quickly, and the diagnosis ranks the right cause. Everything plotted here is
already printed as a number by :mod:`mdia_eval.report` and :mod:`mdia_eval.scorecard` —
the picture is for the reader, never the source of the figure.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import matplotlib

# No display on the machines this runs on, and none needed to write a file.
matplotlib.use("Agg")

import matplotlib.pyplot as plt

from mdia_eval.report import TARGET_DAYS_TO_DETECT, TARGET_RECALL

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from matplotlib.axes import Axes

    from mdia_eval.detection import Score
    from mdia_eval.diagnosis import DiagnosisScore

# Ink and a muted fill, to sit next to the product's own palette.
INK = "#1c1a17"
FILL = "#8a8578"
MARK = "#b45309"


def write(
    directory: Path,
    detected: Score,
    *,
    diagnosed: DiagnosisScore | None = None,
) -> list[Path]:
    """Write every figure the given results support; returns the files created."""
    directory.mkdir(parents=True, exist_ok=True)
    written = [
        _save(directory / "detection-by-scenario.png", _recall_by_kind, detected),
        _save(directory / "days-to-detect.png", _days_to_detect, detected),
    ]
    if diagnosed is not None and diagnosed.cases:
        written.append(_save(directory / "diagnosis-by-scenario.png", _top3_by_kind, diagnosed))
    return written


def _recall_by_kind(ax: Axes, result: Score) -> None:
    within = result.recall_by_kind(TARGET_DAYS_TO_DETECT)
    kinds = list(within)
    ax.barh(kinds, [hit / total for hit, total in (within[kind] for kind in kinds)], color=FILL)
    ax.axvline(TARGET_RECALL, color=MARK, linestyle="--", linewidth=1)
    ax.set_xlim(0, 1)
    ax.set_xlabel(f"detected within {TARGET_DAYS_TO_DETECT} days")
    ax.set_title("Detection by scenario type")


def _days_to_detect(ax: Axes, result: Score) -> None:
    days = result.days_to_detect
    ax.hist(days, bins=range(0, max(days, default=1) + 2), color=FILL, edgecolor=INK, linewidth=0.5)
    ax.axvline(TARGET_DAYS_TO_DETECT, color=MARK, linestyle="--", linewidth=1)
    ax.set_xlabel("days from the scenario's first day")
    ax.set_ylabel("scenarios")
    ax.set_title("How long a scenario takes to surface")


def _top3_by_kind(ax: Axes, result: DiagnosisScore) -> None:
    by_kind = result.by_kind()
    kinds = list(by_kind)
    ax.barh(kinds, [by_kind[k][1] / by_kind[k][2] for k in kinds], color=FILL, label="top 3")
    ax.barh(
        kinds,
        [by_kind[k][0] / by_kind[k][2] for k in kinds],
        color=INK,
        height=0.4,
        label="top 1",
    )
    ax.set_xlim(0, 1)
    ax.set_xlabel("right cause")
    ax.set_title(f"Diagnosis by scenario type ({result.source})")
    ax.legend(loc="lower right", frameon=False)


def _save[T](path: Path, draw: Callable[[Axes, T], None], result: T) -> Path:
    figure, ax = plt.subplots(figsize=(7, 4), dpi=150)
    draw(ax, result)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    figure.tight_layout()
    figure.savefig(path, transparent=False)
    plt.close(figure)
    return path
