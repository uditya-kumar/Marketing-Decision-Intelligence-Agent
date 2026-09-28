"""Plot CTR decay under creative fatigue against the no-scenario counterfactual.

    uv run python scripts/plot_fatigue.py [--creative ig_reels_young_c1] [--out output/fatigue.png]

Top panel: the creative's daily CTR with and without the scenario; bottom panel: its daily
frequency (impressions / reach). CTR should fall once frequency climbs, then recover after the
event ends (the creative is rotated and the exposure stock decays).
"""

from __future__ import annotations

import argparse
from datetime import date, timedelta
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from novawear_sim.config.loader import load_world
from novawear_sim.config.schedule import Schedule, ScheduledEvent, Target
from novawear_sim.engine import Simulation, simulate

START = date(2026, 1, 20)
DAYS = 14


def creative_series(sim: Simulation, creative: str) -> tuple[np.ndarray, np.ndarray]:
    slots = sim.world.slots.creative == sim.world.index_of("creative", creative)
    d = sim.delivery
    clicks = d.clicks[:, slots].sum(axis=1)
    impressions = d.impressions[:, slots].sum(axis=1)
    reach = d.reach[:, slots].sum(axis=1)
    return clicks / np.maximum(impressions, 1), impressions / np.maximum(reach, 1)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--creative", default="ig_reels_young_c1")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", type=Path, default=Path("output/fatigue.png"))
    args = parser.parse_args()

    config = load_world()
    end = START + timedelta(days=DAYS + 30)
    event = ScheduledEvent(
        id="plot",
        type="creative_fatigue",
        start=START,
        days=DAYS,
        target=Target(creative=args.creative),
    )
    base = simulate(config, Schedule(), args.seed, end)
    fatigued = simulate(config, Schedule(events=[event]), args.seed, end)

    window = base.timeline.mask(START - timedelta(days=14), end)
    dates = [d for d, keep in zip(base.timeline.dates, window, strict=True) if keep]
    base_ctr, base_freq = creative_series(base, args.creative)
    ctr, freq = creative_series(fatigued, args.creative)

    fig, (top, bottom) = plt.subplots(2, 1, sharex=True, figsize=(10, 6))
    top.plot(dates, base_ctr[window] * 100, label="counterfactual", color="0.6")
    top.plot(dates, ctr[window] * 100, label="creative_fatigue", color="C3")
    top.set_ylabel("CTR (%)")
    top.legend()
    bottom.plot(dates, base_freq[window], color="0.6")
    bottom.plot(dates, freq[window], color="C3")
    bottom.set_ylabel("Frequency")
    for ax in (top, bottom):
        ax.axvspan(START, event.end, color="C3", alpha=0.08)
    fig.suptitle(f"Creative fatigue — {args.creative} (seed {args.seed})")
    fig.autofmt_xdate()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.out, dpi=120, bbox_inches="tight")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
