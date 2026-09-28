"""``mdia-eval`` — run the harness from the command line."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import httpx
import typer
from mdia.domain.scoring import MIN_SCORE

from mdia_eval import detection, facts, report, settings, truth
from mdia_eval.replay import covered, replay

app = typer.Typer(add_completion=False, help="MDIA evaluation harness (FR-13).")

_ROOT = Path(__file__).resolve().parents[3]
_DATA = _ROOT / "generator" / "output" / "evaluation"
_WORLD = _ROOT / "generator" / "src" / "novawear_sim" / "config" / "world.yaml"

DataDir = Annotated[Path, typer.Option("--data", help="Generator output directory to score.")]
WorldFile = Annotated[Path, typer.Option("--world", help="Generator world file for settings.")]


@app.command()
def detect(
    data: DataDir = _DATA,
    world: WorldFile = _WORLD,
    min_score: Annotated[float, typer.Option(help="Drop signals scoring below this.")] = MIN_SCORE,
    festive: Annotated[
        bool, typer.Option(help="Suppress signals in declared sale windows.")
    ] = True,
    alarms: Annotated[bool, typer.Option(help="List the loudest unexplained alerts.")] = False,
) -> None:
    """Score detection against ground truth (FR-13.1)."""
    loaded = facts.load(data)
    business = settings.load(world)
    events = truth.load(data / "ground_truth.json", facts.lineage(loaded.ads))
    runs = replay(loaded, business, festive=festive, min_score=min_score)
    found = detection.episodes(runs)
    result = detection.split_suppressed(
        detection.score(found, events, covered(runs)), business.festive if festive else ()
    )
    typer.echo(report.detection(result, runs))
    if alarms:
        typer.echo("")
        typer.echo(report.false_positives(result))


@app.command()
def upload(
    data: DataDir = _DATA,
    api: Annotated[str, typer.Option(help="Base URL of a running MDIA backend.")] = (
        "http://localhost:8000/api/v1"
    ),
    timeout: Annotated[float, typer.Option(help="Seconds to wait per request.")] = 600.0,
) -> None:
    """Upload a dataset's exports to a running backend, one source at a time.

    Use a database branch of its own: the evaluation schedule overlaps the demo data.
    """
    for path in sorted(data.glob("*.csv")):
        files = {"files": (path.name, path.read_bytes(), "text/csv")}
        response = httpx.post(f"{api}/ingestion/upload", files=files, timeout=timeout)
        response.raise_for_status()
        for run in response.json()["runs"]:
            typer.echo(
                f"{run['source']:<16}{run['rows_accepted']:>7,} accepted "
                f"{run['rows_rejected']:>5,} rejected"
            )


if __name__ == "__main__":
    app()
