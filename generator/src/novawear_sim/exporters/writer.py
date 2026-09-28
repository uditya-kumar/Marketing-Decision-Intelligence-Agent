"""Write one output window: the four platform CSVs plus `ground_truth.json`."""

from __future__ import annotations

from typing import TYPE_CHECKING

from novawear_sim import __version__
from novawear_sim.exporters.google_ads import google_ads_frame
from novawear_sim.exporters.meta_ads import meta_ads_frame
from novawear_sim.exporters.store import store_orders_frame
from novawear_sim.exporters.web import web_analytics_frame
from novawear_sim.scenarios.ground_truth import GroundTruth

if TYPE_CHECKING:
    from collections.abc import Callable
    from datetime import date
    from pathlib import Path

    import pandas as pd

    from novawear_sim.engine import Simulation

GROUND_TRUTH_FILE = "ground_truth.json"
EXPORTS: dict[str, Callable[[Simulation, date, date], pd.DataFrame]] = {
    "google_ads.csv": google_ads_frame,
    "meta_ads.csv": meta_ads_frame,
    "web_analytics.csv": web_analytics_frame,
    "store_orders.csv": store_orders_frame,
}


def write_window(
    sim: Simulation, schedule: str, start: date, end: date, out_dir: Path
) -> dict[str, int]:
    """Write every export for `start..end` into `out_dir`; returns rows written per file."""
    out_dir.mkdir(parents=True, exist_ok=True)
    counts: dict[str, int] = {}
    for filename, build in EXPORTS.items():
        frame = build(sim, start, end)
        frame.to_csv(out_dir / filename, index=False, lineterminator="\n")
        counts[filename] = len(frame)
    truth = GroundTruth.for_window(
        sim.events, version=__version__, seed=sim.seed, schedule=schedule, start=start, end=end
    )
    truth.write(out_dir / GROUND_TRUTH_FILE)
    counts[GROUND_TRUTH_FILE] = len(truth.events)
    return counts
