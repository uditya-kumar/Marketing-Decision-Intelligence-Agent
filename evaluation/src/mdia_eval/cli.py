"""``mdia-eval`` — run the harness from the command line."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import httpx
import typer
from dotenv import load_dotenv
from mdia.agents.llm import get_chat_model
from mdia.db.session import session_scope
from mdia.domain.scoring import MIN_SCORE

from mdia_eval import diagnosis, grounding, harness, plots, report, scorecard, trust

app = typer.Typer(add_completion=False, help="MDIA evaluation harness (FR-13).")

_ROOT = Path(__file__).resolve().parents[3]
_DATA = _ROOT / "generator" / "output" / "evaluation"
_WORLD = _ROOT / "generator" / "src" / "novawear_sim" / "config" / "world.yaml"
_OUT = Path("output")
# The model provider and the database live in the backend's environment; the harness is
# run from its own directory, so load that file before anything asks for a setting.
load_dotenv(_ROOT / "backend" / ".env")

DataDir = Annotated[Path, typer.Option("--data", help="Generator output directory to score.")]
WorldFile = Annotated[Path, typer.Option("--world", help="Generator world file for settings.")]
MinScore = Annotated[float, typer.Option(help="Drop signals scoring below this.")]
Festive = Annotated[bool, typer.Option(help="Suppress signals in declared sale windows.")]
UseLlm = Annotated[bool, typer.Option("--llm/--no-llm", help="Diagnose with the model too.")]
Limit = Annotated[int, typer.Option(help="Diagnose at most this many scenarios (0 = all).")]


@app.command()
def detect(
    data: DataDir = _DATA,
    world: WorldFile = _WORLD,
    min_score: MinScore = MIN_SCORE,
    festive: Festive = True,
    alarms: Annotated[bool, typer.Option(help="List the loudest unexplained alerts.")] = False,
) -> None:
    """Score detection against ground truth (FR-13.1)."""
    replayed = harness.run(data, world, min_score=min_score, festive=festive)
    typer.echo(report.detection(replayed.detected, replayed.runs))
    if alarms:
        typer.echo("")
        typer.echo(report.false_positives(replayed.detected))


@app.command()
def diagnose(
    data: DataDir = _DATA,
    world: WorldFile = _WORLD,
    min_score: MinScore = MIN_SCORE,
    festive: Festive = True,
    llm: UseLlm = False,
    limit: Limit = 0,
) -> None:
    """Score diagnosis of everything detected (FR-13.2); ``--llm`` adds the model's run."""
    replayed = harness.run(data, world, min_score=min_score, festive=festive)
    rules, model = _diagnose(replayed, llm=llm, limit=limit)
    typer.echo(scorecard.diagnosis(model or rules, rules if model else None))
    if model is not None:
        typer.echo("")
        typer.echo(scorecard.grounding(grounding.score(model.calls)))


@app.command("trust")
def trust_report(
    data: DataDir = _DATA,
    world: WorldFile = _WORLD,
    min_score: MinScore = MIN_SCORE,
    festive: Festive = True,
) -> None:
    """Score tracking-break detection and suppression (FR-13.3)."""
    replayed = harness.run(data, world, min_score=min_score, festive=festive)
    typer.echo(scorecard.trust(trust.score(replayed.runs, replayed.events)))


@app.command("grounding")
def grounding_report(
    purpose: Annotated[str, typer.Option(help='Only "diagnosis" or only "report" calls.')] = "",
) -> None:
    """Score the grounding guard from what a running backend logged (FR-13.4)."""
    with session_scope() as session:
        result = grounding.from_db(session, purpose=purpose or None)
    typer.echo(scorecard.grounding(result))


@app.command("all")
def run_all(
    data: DataDir = _DATA,
    world: WorldFile = _WORLD,
    min_score: MinScore = MIN_SCORE,
    festive: Festive = True,
    llm: UseLlm = False,
    limit: Limit = 0,
    db: Annotated[bool, typer.Option(help="Read logged LLM calls from the database too.")] = False,
    out: Annotated[Path, typer.Option("--out", help="Where to write the tables and plots.")] = _OUT,
) -> None:
    """Every §13 criterion, printed and written to ``--out`` with the thesis figures."""
    replayed = harness.run(data, world, min_score=min_score, festive=festive)
    rules, model = _diagnose(replayed, llm=llm, limit=limit)
    diagnosed = model or rules
    trusted = trust.score(replayed.runs, replayed.events)
    grounded = _grounding(diagnosed, db=db)
    sections = [
        scorecard.scorecard(
            replayed.detected, diagnosed=diagnosed, trusted=trusted, grounded=grounded
        ),
        report.detection(replayed.detected, replayed.runs),
        scorecard.diagnosis(diagnosed, rules if model else None),
        scorecard.trust(trusted),
    ]
    if grounded is not None:
        sections.append(scorecard.grounding(grounded))
    text = "\n\n".join(sections)
    # Written before anything is printed: a model run costs minutes, and a console that
    # cannot encode a character must not be what throws the results away.
    out.mkdir(parents=True, exist_ok=True)
    (out / "scorecard.txt").write_text(f"{text}\n", encoding="utf-8")
    written = plots.write(out, replayed.detected, diagnosed=diagnosed)
    typer.echo(text)
    typer.echo("")
    typer.echo(f"Written: {out / 'scorecard.txt'}")
    for path in written:
        typer.echo(f"         {path}")


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


def _diagnose(
    replayed: harness.Replayed, *, llm: bool, limit: int
) -> tuple[diagnosis.DiagnosisScore, diagnosis.DiagnosisScore | None]:
    """The rules always, and the model as well when asked for and configured."""
    cases = limit or None
    rules = diagnosis.score(replayed.runs, replayed.detected, limit=cases)
    if not llm:
        return rules, None
    model = get_chat_model()
    if model is None:
        raise typer.BadParameter("No LLM provider is configured; run with --no-llm.")
    return rules, diagnosis.score(replayed.runs, replayed.detected, model=model, limit=cases)


def _grounding(diagnosed: diagnosis.DiagnosisScore, *, db: bool) -> grounding.GroundingScore | None:
    """Logged calls if asked for, otherwise whatever this run itself asked the model."""
    if db:
        with session_scope() as session:
            return grounding.from_db(session)
    return grounding.score(diagnosed.calls) if diagnosed.calls else None


if __name__ == "__main__":
    app()
