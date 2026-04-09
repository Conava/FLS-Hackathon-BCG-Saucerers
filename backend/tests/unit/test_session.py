"""Unit tests for app.db.session — TDD Red phase first."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession


def test_engine_constructed_with_asyncpg_driver() -> None:
    """Engine URL must use postgresql+asyncpg:// scheme (not bare postgresql://)."""
    from app.db.session import get_engine

    engine = get_engine(database_url="postgresql+asyncpg://user:pass@localhost:5432/testdb")
    assert engine.url.drivername == "postgresql+asyncpg"


async def test_get_session_yields_asyncsession() -> None:
    """get_session must yield an AsyncSession instance (FastAPI dependency contract)."""
    from app.db.session import get_session

    # get_session is an async generator; we just verify the first yielded value is an AsyncSession.
    # We pass a fake URL so no real DB connection is attempted.
    gen = get_session(
        database_url="postgresql+asyncpg://user:pass@localhost:5432/testdb"
    )
    session = await gen.__anext__()
    try:
        assert isinstance(session, AsyncSession)
    finally:
        # Clean up: close generator without hitting the DB commit/close path
        await gen.aclose()


def test_validate_url_rewrites_bare_postgresql() -> None:
    """_validate_url rewrites bare ``postgresql://`` to ``postgresql+asyncpg://``."""
    from app.db.session import _validate_url

    result = _validate_url("postgresql://user:pass@localhost:5432/db")
    assert result == "postgresql+asyncpg://user:pass@localhost:5432/db"


def test_validate_url_rejects_invalid_scheme() -> None:
    """_validate_url raises ValueError for unsupported URL schemes."""
    from app.db.session import _validate_url

    with pytest.raises(ValueError, match="postgresql\\+asyncpg"):
        _validate_url("mysql://user:pass@localhost:3306/db")
