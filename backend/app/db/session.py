"""Async SQLAlchemy 2.0 engine + session factory for the Longevity+ backend.

Design decisions
----------------
* Engine construction is lazy (``get_engine`` factory with ``@lru_cache``) so
  importing this module never opens a DB connection and never fails if the
  ``DATABASE_URL`` environment variable is absent at import time.
* ``app.core.config`` is imported *inside* ``_settings_database_url()`` — not
  at module top level — so this module can be imported in isolation while T3
  (core/config) is being built in a parallel wave.  The helper is annotated
  ``-> str`` with a per-line ``ignore`` that covers both the "module missing"
  and "module untyped" mypy states.
* The ``database_url`` parameter on both public functions is optional and
  defaults to the Settings singleton when omitted.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def _settings_database_url() -> str:
    """Return ``database_url`` from ``app.core.config.Settings``.

    Imported lazily so callers do not need T3 to be present at import time.
    The ``type: ignore`` below covers the "module not yet installed" state;
    once T3 merges the ignore becomes dead but harmless (ruff ``noqa``
    suppresses the unused-ignore warning).
    """
    from app.core.config import Settings  # type: ignore[import-untyped]  # noqa: PGH003

    return str(Settings().database_url)


def _validate_url(url: str) -> str:
    """Ensure the URL uses the asyncpg driver scheme.

    Bare ``postgresql://`` URLs silently break asyncpg.  We rewrite them here
    to catch misconfiguration early rather than at first DB call.
    """
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if not url.startswith("postgresql+asyncpg://"):
        raise ValueError(
            f"database_url must use 'postgresql+asyncpg://' scheme, got: {url!r}"
        )
    return url


@lru_cache(maxsize=1)
def get_engine(database_url: str | None = None) -> AsyncEngine:
    """Return the singleton ``AsyncEngine``, constructing it on first call.

    The engine is cached via ``@lru_cache`` so the underlying connection pool
    is shared across all callers.  No connection is opened during construction
    (``pool_pre_ping=True`` verifies connectivity only on checkout).

    Args:
        database_url: Optional URL override.  When ``None`` the value is read
            from ``app.core.config.Settings`` via a lazy import (safe before
            T3 merges).

    Returns:
        A configured ``AsyncEngine`` using the ``asyncpg`` dialect.
    """
    resolved: str = database_url if database_url is not None else _settings_database_url()
    url = _validate_url(resolved)
    return create_async_engine(
        url,
        pool_pre_ping=True,
        # echo defaults to False; override per environment as needed
    )


def _make_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Create a session factory bound to *engine*.

    ``expire_on_commit=False`` is required for async usage: after ``commit``
    SQLAlchemy must not issue lazy-load SQL on expired attributes because there
    is no synchronous fallback in async mode.
    """
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_session(
    database_url: str | None = None,
) -> AsyncIterator[AsyncSession]:
    """FastAPI dependency that yields an ``AsyncSession`` per request.

    Usage in a router::

        @router.get("/patients/{patient_id}")
        async def get_patient(
            patient_id: str,
            session: AsyncSession = Depends(get_session),
        ) -> PatientProfileOut:
            ...

    The session is closed automatically after the response is sent.  Any
    exception propagates upward; no explicit rollback is performed here.

    Args:
        database_url: Optional URL override for testing.  When ``None`` the
            singleton engine from ``get_engine()`` is used.
    """
    engine = get_engine(database_url)
    session_factory = _make_session_factory(engine)
    async with session_factory() as session:
        yield session


# ---------------------------------------------------------------------------
# FastAPI-compatible dependency alias (no extra parameters — uses env config)
# ---------------------------------------------------------------------------

SessionDep = Annotated[AsyncSession, Depends(get_session)]
