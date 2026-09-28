"""API DTOs for ingestion: upload results, run history, source status, templates."""

from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

from mdia.domain.sources import Source
from mdia.models.ingestion import RunStatus

if TYPE_CHECKING:
    from mdia.ingestion.templates import SourceTemplate


class _FromAttributes(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class RejectedRowOut(_FromAttributes):
    line: int
    errors: list[str]
    values: dict[str, str]


class IngestionRunOut(_FromAttributes):
    id: int
    source: Source | None
    file_name: str
    status: RunStatus
    rows_total: int
    rows_accepted: int
    rows_rejected: int
    date_from: dt.date | None
    date_to: dt.date | None
    rejected_rows: list[RejectedRowOut]
    error: str | None
    created_at: dt.datetime


class SourceStatusOut(_FromAttributes):
    source: Source
    label: str
    first_date: dt.date | None
    last_date: dt.date | None
    rows: int
    days: int


class IngestionStatusOut(_FromAttributes):
    as_of_date: dt.date | None
    sources: list[SourceStatusOut]
    missing_sources: list[Source]


class UploadResponse(_FromAttributes):
    runs: list[IngestionRunOut]
    status: IngestionStatusOut


class TemplateColumnOut(BaseModel):
    header: str
    type: str
    stored: bool


class TemplateOut(BaseModel):
    source: Source
    label: str
    columns: list[TemplateColumnOut]
    csv_header: str

    @classmethod
    def from_template(cls, template: SourceTemplate) -> TemplateOut:
        return cls(
            source=template.source,
            label=template.label,
            columns=[
                TemplateColumnOut(header=c.header, type=c.parser.kind, stored=c.stored)
                for c in template.columns
            ],
            csv_header=",".join(template.headers),
        )
