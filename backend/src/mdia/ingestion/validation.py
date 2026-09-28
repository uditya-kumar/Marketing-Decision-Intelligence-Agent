"""Row-level validation: raw CSV rows → canonical records + a rejected-row report."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    from mdia.ingestion.templates import Record, SourceTemplate


def normalise_header(header: str) -> str:
    """Compare headers ignoring case, surrounding whitespace and a UTF-8 BOM."""
    return header.lstrip("\N{ZERO WIDTH NO-BREAK SPACE}").strip().casefold()


@dataclass(frozen=True, slots=True)
class RejectedRow:
    line: int
    errors: tuple[str, ...]
    values: dict[str, str]


@dataclass(slots=True)
class ValidationResult:
    records: list[Record] = field(default_factory=list)
    rejected: list[RejectedRow] = field(default_factory=list)


def validate_rows(
    template: SourceTemplate,
    headers: Sequence[str],
    rows: Iterable[tuple[int, Sequence[str]]],
) -> ValidationResult:
    """Validate ``(line_number, cells)`` rows against ``template``.

    A row is rejected, with every reason found, if a cell fails to parse, a
    cross-field check fails, or it repeats the natural key of an earlier row.
    Blank rows are skipped silently since spreadsheets often leave them at the end.
    """
    positions = {normalise_header(header): i for i, header in enumerate(headers)}
    columns = [(column, positions[normalise_header(column.header)]) for column in template.columns]
    dropped = [column.field for column in template.columns if not column.stored]
    seen: dict[tuple[object, ...], int] = {}
    result = ValidationResult()

    for line, cells in rows:
        if not any(cell.strip() for cell in cells):
            continue
        values = dict(zip(headers, cells, strict=False))
        if len(cells) != len(headers):
            reason = f"expected {len(headers)} columns, found {len(cells)}"
            result.rejected.append(RejectedRow(line, (reason,), values))
            continue

        record: Record = dict(template.constants)
        errors: list[str] = []
        for column, position in columns:
            raw = cells[position].strip()
            if not raw:
                errors.append(f"{column.header}: value is missing")
                continue
            try:
                record[column.field] = column.parser.parse(raw)
            except ValueError as exc:
                errors.append(f"{column.header}: {exc} (got {raw!r})")
        if not errors:
            reasons = (check(record) for check in template.checks)
            errors = [reason for reason in reasons if reason is not None]
        if not errors:
            key = tuple(record[name] for name in template.key)
            if key in seen:
                errors.append(f"duplicate of line {seen[key]}")
            else:
                seen[key] = line

        if errors:
            result.rejected.append(RejectedRow(line, tuple(errors), values))
            continue
        if template.derive is not None:
            record = template.derive(record)
        for name in dropped:
            del record[name]
        result.records.append(record)
    return result
