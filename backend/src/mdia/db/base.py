"""SQLAlchemy declarative base.

All ORM models inherit from :class:`Base`. Kept import-light so Alembic can import
model metadata without pulling in the whole app.
"""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base for all MDIA ORM models."""
