"""Database engine and session management.

The engine is created lazily from settings so that importing this module never
requires a live database. Use :func:`get_session` as a FastAPI dependency.
"""

from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from mdia.core.settings import get_settings

if TYPE_CHECKING:
    from collections.abc import Iterator


@lru_cache
def get_engine() -> Engine:
    """Return the process-wide SQLAlchemy engine (created once)."""
    settings = get_settings()
    return create_engine(settings.sqlalchemy_url, pool_pre_ping=True, future=True)


@lru_cache
def _get_sessionmaker() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)


def get_session() -> Iterator[Session]:
    """FastAPI dependency yielding a session that is always closed."""
    session = _get_sessionmaker()()
    try:
        yield session
    finally:
        session.close()


def check_database() -> bool:
    """Return ``True`` if a trivial query succeeds against the configured database."""
    with get_engine().connect() as conn:
        conn.execute(text("SELECT 1"))
    return True
