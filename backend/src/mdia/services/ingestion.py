"""Ingestion use case: uploaded CSVs → validated facts + run log + as-of date."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING

import structlog
from sqlalchemy.exc import SQLAlchemyError

from mdia.core.errors import ValidationError
from mdia.domain.trust import as_of_date, missing_sources
from mdia.ingestion.reader import read_csv
from mdia.ingestion.templates import TEMPLATES
from mdia.models import IngestionRun
from mdia.repositories.facts import FactRepository
from mdia.repositories.ingestion_runs import IngestionRunRepository

if TYPE_CHECKING:
    import datetime as dt
    from collections.abc import Sequence

    from sqlalchemy.orm import Session

    from mdia.domain.sources import Source
    from mdia.ingestion.reader import Batch
    from mdia.ingestion.templates import SourceTemplate
    from mdia.models.ingestion import RunStatus

log = structlog.get_logger(__name__)

MAX_FILE_BYTES = 50 * 1024 * 1024
# Enough rejected rows to spot the pattern without bloating the run log.
REJECTED_SAMPLE_SIZE = 200


@dataclass(frozen=True, slots=True)
class UploadedFile:
    name: str
    content: bytes


@dataclass(frozen=True, slots=True)
class SourceStatus:
    source: Source
    label: str
    first_date: dt.date | None
    last_date: dt.date | None
    rows: int
    days: int


@dataclass(frozen=True, slots=True)
class IngestionStatus:
    as_of_date: dt.date | None
    sources: list[SourceStatus]
    missing_sources: list[Source]


@dataclass(frozen=True, slots=True)
class UploadResult:
    runs: list[IngestionRun]
    status: IngestionStatus


class IngestionService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._facts = FactRepository(session)
        self._runs = IngestionRunRepository(session)

    @staticmethod
    def templates() -> tuple[SourceTemplate, ...]:
        return TEMPLATES

    def upload(self, files: Sequence[UploadedFile]) -> UploadResult:
        """Ingest each file in its own transaction so one bad file can't block the rest."""
        runs = [self._ingest(file) for file in files]
        return UploadResult(runs, self.status())

    def recent_runs(self, limit: int) -> Sequence[IngestionRun]:
        return self._runs.list_recent(limit)

    def status(self) -> IngestionStatus:
        coverage = {c.source: c for c in self._facts.coverage()}
        latest = {source: c.last_date for source, c in coverage.items()}
        sources = [
            SourceStatus(t.source, t.label, None, None, 0, 0)
            if (c := coverage.get(t.source)) is None
            else SourceStatus(t.source, t.label, c.first_date, c.last_date, c.rows, c.days)
            for t in TEMPLATES
        ]
        return IngestionStatus(as_of_date(latest), sources, missing_sources(latest))

    def _ingest(self, file: UploadedFile) -> IngestionRun:
        try:
            if len(file.content) > MAX_FILE_BYTES:
                raise ValidationError(f"The file is larger than {MAX_FILE_BYTES // 2**20} MB.")
            batch = read_csv(file.content)
        except ValidationError as exc:
            return self._save(_failed_run(file.name, None, str(exc)))

        run = _run_for(file.name, batch)
        try:
            self._load(batch)
            saved = self._save(run)
        except SQLAlchemyError:
            self._session.rollback()
            log.exception("ingestion.load_failed", file=file.name, source=batch.source)
            error = "The database rejected this file; no rows were saved."
            return self._save(_failed_run(file.name, batch.source, error))
        log.info(
            "ingestion.run",
            file=file.name,
            source=run.source,
            status=run.status,
            accepted=run.rows_accepted,
            rejected=run.rows_rejected,
        )
        return saved

    def _load(self, batch: Batch) -> None:
        match batch.template.kind:
            case "ad":
                self._facts.upsert_ad_records(batch.records, batch.template.label)
            case "web":
                self._facts.upsert_web_records(batch.records)
            case "store":
                self._facts.upsert_store_records(batch.records)

    def _save(self, run: IngestionRun) -> IngestionRun:
        self._runs.add(run)
        self._session.commit()
        return run


def _run_for(file_name: str, batch: Batch) -> IngestionRun:
    accepted, rejected = len(batch.records), len(batch.rejected)
    status: RunStatus = "failed" if not accepted else "partial" if rejected else "success"
    error = None
    if not accepted:
        error = "Every row was rejected." if rejected else "The file has no data rows."
    date_from, date_to = batch.date_range or (None, None)
    return IngestionRun(
        source=batch.source,
        file_name=file_name,
        status=status,
        rows_total=batch.rows_total,
        rows_accepted=accepted,
        rows_rejected=rejected,
        date_from=date_from,
        date_to=date_to,
        rejected_rows=[asdict(row) for row in batch.rejected[:REJECTED_SAMPLE_SIZE]],
        error=error,
    )


def _failed_run(file_name: str, source: Source | None, error: str) -> IngestionRun:
    return IngestionRun(
        source=source,
        file_name=file_name,
        status="failed",
        rows_total=0,
        rows_accepted=0,
        rows_rejected=0,
        rejected_rows=[],
        error=error,
    )
