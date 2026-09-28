"""`novawear-sim` — write NovaWear platform exports plus ground truth for a date window.

Both commands simulate from the world's epoch so that a `batch` continues a `backfill`
exactly (same seed and schedule ⇒ the batch equals that slice of a longer backfill).
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path

import typer

from novawear_sim.config.loader import load_schedule, load_world
from novawear_sim.engine import simulate
from novawear_sim.errors import GeneratorError
from novawear_sim.exporters.writer import write_window

app = typer.Typer(add_completion=False, no_args_is_help=True, help=__doc__)

SEED = typer.Option(42, help="Random seed; same seed and schedule give identical output.")
SCHEDULE = typer.Option("demo", help="Schedule name from scenarios.yaml ('none' for baseline).")
WORLD = typer.Option(None, help="Alternative world.yaml (defaults to the packaged one).")
SCENARIOS = typer.Option(None, help="Alternative scenarios.yaml (defaults to the packaged one).")


def _parse_date(value: str) -> date:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise typer.BadParameter(f"expected YYYY-MM-DD, got {value!r}") from exc


def _generate(
    start: date,
    end: date,
    seed: int,
    schedule: str,
    out: Path,
    world: Path | None,
    scenarios: Path | None,
) -> None:
    try:
        config = load_world(world)
        sim = simulate(config, load_schedule(schedule, scenarios), seed, end)
        counts = write_window(sim, schedule, start, end, out)
    except GeneratorError as exc:
        typer.secho(f"error: {exc}", err=True, fg=typer.colors.RED)
        raise typer.Exit(code=1) from exc
    typer.echo(f"{start}..{end} (seed {seed}, schedule {schedule!r}) -> {out}")
    for name, rows in counts.items():
        typer.echo(f"  {name:<20} {rows:>7} {'events' if name.endswith('.json') else 'rows'}")


@app.command()
def backfill(
    days: int = typer.Option(180, min=1, help="Number of days of history to write."),
    end: str | None = typer.Option(None, help="Last day (YYYY-MM-DD); defaults to world.yaml."),
    seed: int = SEED,
    schedule: str = SCHEDULE,
    out: Path = typer.Option(Path("output/backfill"), help="Output directory."),
    world: Path | None = WORLD,
    scenarios: Path | None = SCENARIOS,
) -> None:
    """Write `days` of history ending at `end`."""
    try:
        last = _parse_date(end) if end else load_world(world).timeline.default_end
    except GeneratorError as exc:
        typer.secho(f"error: {exc}", err=True, fg=typer.colors.RED)
        raise typer.Exit(code=1) from exc
    _generate(last - timedelta(days=days - 1), last, seed, schedule, out, world, scenarios)


@app.command()
def batch(
    start: str = typer.Option(..., "--from", help="First day of the batch (YYYY-MM-DD)."),
    days: int = typer.Option(7, min=1, help="Number of days in the batch."),
    seed: int = SEED,
    schedule: str = SCHEDULE,
    out: Path | None = typer.Option(None, help="Output directory [default: output/batch_<from>]."),
    world: Path | None = WORLD,
    scenarios: Path | None = SCENARIOS,
) -> None:
    """Write a follow-up batch of `days` starting at `--from`."""
    first = _parse_date(start)
    target = out or Path(f"output/batch_{first.isoformat()}")
    _generate(first, first + timedelta(days=days - 1), seed, schedule, target, world, scenarios)
