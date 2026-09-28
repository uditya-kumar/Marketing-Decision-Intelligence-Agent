"""Cell parsers used by source templates.

Each parser turns one raw CSV cell into a typed value or raises ``ValueError`` with a
reason a marketer can act on; the reason ends up in the rejected-row report.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

# Upper bounds of the storage columns (INTEGER, NUMERIC(14, 2)); larger values are
# almost certainly corrupt and would otherwise fail the whole file at insert time.
MAX_COUNT = 2_147_483_647
MAX_AMOUNT = Decimal("1e12")


@dataclass(frozen=True, slots=True)
class Parser:
    """A named cell parser; ``kind`` is what the templates endpoint shows users."""

    kind: str
    parse: Callable[[str], Any]


def _date_parser(fmt: str, example: str) -> Parser:
    def parse(raw: str) -> dt.date:
        try:
            return dt.datetime.strptime(raw, fmt).date()
        except ValueError:
            raise ValueError(f"expected a date like {example}") from None

    return Parser(f"date ({example})", parse)


def _decimal(raw: str) -> Decimal:
    try:
        value = Decimal(raw.replace(",", ""))
    except InvalidOperation:
        raise ValueError("expected a number") from None
    if not value.is_finite() or abs(value) >= MAX_AMOUNT:
        raise ValueError("expected a number")
    return value


def _count(raw: str) -> int:
    value = _decimal(raw)
    if value < 0 or value != value.to_integral_value() or value > MAX_COUNT:
        raise ValueError("expected a whole number >= 0")
    return int(value)


def _amount(raw: str) -> Decimal:
    value = _decimal(raw)
    if value < 0:
        raise ValueError("expected a number >= 0")
    return value


def _deduction(raw: str) -> Decimal:
    # Store exports show discounts and returns as negatives; we keep magnitudes.
    return abs(_decimal(raw))


def _text(raw: str) -> str:
    if len(raw) > 255:
        raise ValueError("text is longer than 255 characters")
    return raw


def _identifier(raw: str) -> str:
    # Spreadsheet round-trips turn long IDs into "1.20284E+17"; catch that early.
    if not raw.isdigit() or len(raw) > 32:
        raise ValueError("expected a numeric ID (was the file re-saved from a spreadsheet?)")
    return raw


def choice(mapping: Mapping[str, str]) -> Parser:
    """Accept any key of ``mapping`` (case-insensitive) and return its canonical value."""
    lookup = {key.casefold(): value for key, value in mapping.items()}
    allowed = ", ".join(mapping)

    def parse(raw: str) -> str:
        try:
            return lookup[raw.casefold()]
        except KeyError:
            raise ValueError(f"expected one of: {allowed}") from None

    return Parser(f"one of: {allowed}", parse)


ISO_DATE = _date_parser("%Y-%m-%d", "2026-10-14")
COMPACT_DATE = _date_parser("%Y%m%d", "20261014")
COUNT = Parser("whole number >= 0", _count)
AMOUNT = Parser("number >= 0", _amount)
SIGNED_AMOUNT = Parser("number", _decimal)
DEDUCTION = Parser("number (sign ignored)", _deduction)
TEXT = Parser("text", _text)
IDENTIFIER = Parser("numeric ID", _identifier)
