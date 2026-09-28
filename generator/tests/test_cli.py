from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pandas as pd
from typer.testing import CliRunner

from novawear_sim.cli import app
from novawear_sim.exporters.writer import EXPORTS, GROUND_TRUTH_FILE

if TYPE_CHECKING:
    from pathlib import Path

runner = CliRunner()


def test_backfill_writes_csvs_and_ground_truth(tmp_path: Path) -> None:
    out = tmp_path / "backfill"
    result = runner.invoke(app, ["backfill", "--days", "180", "--seed", "42", "--out", str(out)])
    assert result.exit_code == 0, result.output
    for name in [*EXPORTS, GROUND_TRUTH_FILE]:
        assert (out / name).is_file()
    store = pd.read_csv(out / "store_orders.csv")
    assert len(store) == 180
    assert store["Day"].iloc[-1] == "2026-10-14"
    truth = json.loads((out / GROUND_TRUTH_FILE).read_text(encoding="utf-8"))
    assert truth["schedule"] == "demo" and truth["events"]


def test_batch_writes_the_requested_window(tmp_path: Path) -> None:
    out = tmp_path / "batch"
    args = ["batch", "--from", "2026-10-15", "--days", "7", "--out", str(out)]
    result = runner.invoke(app, args)
    assert result.exit_code == 0, result.output
    days = pd.read_csv(out / "store_orders.csv")["Day"]
    assert list(days) == [f"2026-10-{d}" for d in range(15, 22)]
    assert (out / GROUND_TRUTH_FILE).is_file()


def test_errors_are_reported_without_a_traceback(tmp_path: Path) -> None:
    result = runner.invoke(app, ["batch", "--from", "2020-01-01", "--out", str(tmp_path)])
    assert result.exit_code == 1
    assert "before the world epoch" in result.output
    assert result.exception is None or isinstance(result.exception, SystemExit)


def test_unknown_schedule_is_reported(tmp_path: Path) -> None:
    result = runner.invoke(app, ["backfill", "--schedule", "nope", "--out", str(tmp_path)])
    assert result.exit_code == 1
    assert "unknown schedule" in result.output


def test_bad_date_is_a_usage_error(tmp_path: Path) -> None:
    result = runner.invoke(app, ["batch", "--from", "15/10/2026", "--out", str(tmp_path)])
    assert result.exit_code == 2
