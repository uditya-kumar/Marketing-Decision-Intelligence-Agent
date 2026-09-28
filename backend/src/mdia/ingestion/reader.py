"""Read one uploaded CSV: detect which platform produced it, then validate its rows."""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from typing import TYPE_CHECKING

from mdia.core.errors import UnrecognisedFileError
from mdia.ingestion.templates import TEMPLATES
from mdia.ingestion.validation import normalise_header, validate_rows

if TYPE_CHECKING:
    import datetime as dt
    from collections.abc import Sequence

    from mdia.domain.sources import Source
    from mdia.ingestion.templates import Record, SourceTemplate
    from mdia.ingestion.validation import RejectedRow


@dataclass(frozen=True, slots=True)
class Batch:
    template: SourceTemplate
    records: list[Record]
    rejected: list[RejectedRow]

    @property
    def source(self) -> Source:
        return self.template.source

    @property
    def rows_total(self) -> int:
        return len(self.records) + len(self.rejected)

    @property
    def date_range(self) -> tuple[dt.date, dt.date] | None:
        dates = [record["date"] for record in self.records]
        return (min(dates), max(dates)) if dates else None


def read_csv(content: bytes | str, template: SourceTemplate | None = None) -> Batch:
    """Parse an export into validated records; the source is detected unless given.

    Raises :class:`UnrecognisedFileError` if the file is not UTF-8 text, has no
    header row, or matches no template.
    """
    text = _decode(content) if isinstance(content, bytes) else content
    reader = csv.reader(io.StringIO(text))
    headers = next(reader, [])
    if not any(header.strip() for header in headers):
        raise UnrecognisedFileError("The file is empty or has no header row.")
    template = template or detect_template(headers)
    # line_num counts physical lines, so quoted multi-line cells stay traceable.
    rows = ((reader.line_num, cells) for cells in reader)
    result = validate_rows(template, headers, rows)
    return Batch(template, result.records, result.rejected)


def missing_headers(template: SourceTemplate, headers: Sequence[str]) -> list[str]:
    present = {normalise_header(header) for header in headers}
    return [h for h in template.headers if normalise_header(h) not in present]


def detect_template(
    headers: Sequence[str], templates: Sequence[SourceTemplate] = TEMPLATES
) -> SourceTemplate:
    """Return the template whose columns are all present; extra columns are ignored.

    If several match, the one with the most columns wins, being the more specific.
    Otherwise raise with the closest template's missing columns so the user can fix
    the export instead of guessing.
    """
    matches = [t for t in templates if not missing_headers(t, headers)]
    if matches:
        return max(matches, key=lambda t: len(t.columns))

    def overlap(template: SourceTemplate) -> float:
        return 1 - len(missing_headers(template, headers)) / len(template.columns)

    closest = max(templates, key=overlap)
    if overlap(closest) == 0:
        labels = ", ".join(t.label for t in templates)
        raise UnrecognisedFileError(f"Headers don't match any supported export ({labels}).")
    missing = ", ".join(missing_headers(closest, headers))
    raise UnrecognisedFileError(
        f"Looks like a {closest.label} export but is missing columns: {missing}."
    )


def _decode(content: bytes) -> str:
    try:
        return content.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise UnrecognisedFileError("The file is not UTF-8 encoded CSV text.") from None
