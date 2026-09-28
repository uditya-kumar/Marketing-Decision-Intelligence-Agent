"""Idempotent bulk upsert on a table's primary or unique key (``INSERT … ON CONFLICT``)."""

from __future__ import annotations

from itertools import batched
from typing import TYPE_CHECKING, Any

from sqlalchemy import inspect
from sqlalchemy.dialects.postgresql import insert

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from sqlalchemy.orm import Session

    from mdia.db.base import Base

# Postgres caps a statement at 65,535 bind parameters; 1,000 rows of our widest
# table (14 columns) stays well inside that.
CHUNK_SIZE = 1000


def upsert(
    session: Session,
    model: type[Base],
    rows: Sequence[Mapping[str, Any]],
    key: Sequence[str] | None = None,
) -> None:
    """Insert ``rows``, overwriting non-key columns where ``key`` already exists.

    ``key`` defaults to the primary key. Loading the same rows twice leaves the table
    unchanged, which is what makes re-uploading an export safe. Rows must not repeat
    a key within one call (Postgres cannot update the same row twice per statement).
    """
    conflict_key = list(key or [column.name for column in inspect(model).primary_key])
    for chunk in batched(rows, CHUNK_SIZE):
        stmt = insert(model).values(list(chunk))
        updates = {name: stmt.excluded[name] for name in chunk[0] if name not in conflict_key}
        session.execute(stmt.on_conflict_do_update(index_elements=conflict_key, set_=updates))
