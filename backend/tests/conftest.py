"""Root test configuration: testcontainers Postgres fixtures with per-test rollback.

Fixture hierarchy
-----------------
postgres_container (session-scoped)
    └── engine (session-scoped)
            └── db_session (function-scoped) — rolls back after every test
                    └── app_client (function-scoped) — FastAPI test client wired
                                                        to the test session

Per-test isolation strategy
----------------------------
``db_session`` binds an ``AsyncSession`` to an open *connection-level* transaction
rather than to the engine directly.  At teardown the outer transaction is rolled
back, so every test starts with a clean DB without recreating the schema.

``app_client`` is lazy: it skips cleanly when ``app.main`` is not yet present
(T16 is implemented in a later wave).
"""

# mypy: ignore-errors
from __future__ import annotations

# ---------------------------------------------------------------------------
# Rootless Docker auto-detection
# ---------------------------------------------------------------------------
# uv run does not inherit the shell's DOCKER_HOST, so on rootless-Docker hosts
# (common on Linux without Docker Desktop) `docker.from_env()` falls back to
# /var/run/docker.sock which doesn't exist.  We detect the XDG socket at
# module-load time — before any fixture runs — so every downstream call to
# docker.from_env() finds the right socket without requiring shell config.
import os as _os

_rootless_sock = f"/run/user/{_os.getuid()}/docker.sock"
if not _os.environ.get("DOCKER_HOST") and _os.path.exists(_rootless_sock):
    _os.environ["DOCKER_HOST"] = f"unix://{_rootless_sock}"

from collections.abc import AsyncIterator  # noqa: E402

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine  # noqa: E402
from sqlmodel import SQLModel  # noqa: E402
from testcontainers.postgres import PostgresContainer  # noqa: E402


def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers so pytest does not emit unknown-mark warnings."""
    config.addinivalue_line(
        "markers",
        "integration: marks tests that require a real Postgres via testcontainers",
    )


# ---------------------------------------------------------------------------
# Session-scoped container
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def postgres_container() -> AsyncIterator[PostgresContainer]:
    """Start a pgvector/pg16 container for the entire test session.

    The context-manager form is used so testcontainers handles startup/teardown.
    We wrap it in a generator so pytest-asyncio can inject it as a fixture.

    Skips automatically when Docker daemon is not available (e.g., on developer
    machines without Docker Desktop / rootless Docker installed).
    """
    import docker

    try:
        docker.from_env()
    except Exception:
        pytest.skip("Docker daemon not available — skipping testcontainers tests")

    with PostgresContainer("pgvector/pgvector:pg16") as pg:
        yield pg


# ---------------------------------------------------------------------------
# Session-scoped async engine
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def engine(postgres_container: PostgresContainer) -> AsyncIterator[AsyncEngine]:
    """Create an async SQLAlchemy engine pointed at the testcontainers Postgres.

    Steps:
    1. Build the connection URL using the asyncpg driver.
    2. Enable the pgvector extension.
    3. Create all SQLModel-registered tables once per session.
    """
    # Import models to register their metadata with SQLModel before create_all.
    import app.models  # noqa: F401 — side-effect import registers tables

    url = postgres_container.get_connection_url(driver="asyncpg")

    eng = create_async_engine(url, pool_pre_ping=True)
    async with eng.begin() as conn:
        await conn.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS vector")
        await conn.run_sync(SQLModel.metadata.create_all)

    yield eng

    await eng.dispose()


# ---------------------------------------------------------------------------
# Function-scoped session with per-test rollback
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(loop_scope="session")
async def db_session(engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    """Yield an ``AsyncSession`` whose changes are rolled back after every test.

    We bind the session to an open *connection* transaction rather than the
    engine.  After the test, we roll back the outer transaction, leaving the
    schema pristine for the next test — no table truncation needed.

    ``loop_scope="session"`` is required: the engine is created in the session-
    scoped event loop, and asyncpg connections must stay on the same loop.
    Without this, pytest-asyncio would run this fixture in a function-scoped
    loop, causing "Future attached to a different loop" errors.
    """
    async with engine.connect() as conn:
        trans = await conn.begin()
        async_session = AsyncSession(bind=conn, expire_on_commit=False)
        try:
            yield async_session
        finally:
            await async_session.close()
            await trans.rollback()


# ---------------------------------------------------------------------------
# Function-scoped FastAPI test client (lazy — skips if app.main is absent)
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(loop_scope="session")
async def app_client(db_session: AsyncSession):  # type: ignore[return]
    """Yield an ``httpx.AsyncClient`` wired to the test ``db_session``.

    This fixture skips cleanly when ``app.main`` has not been implemented yet
    (T16).  Once T16 merges, the skip is automatically lifted.
    """
    pytest.importorskip("app.main")

    from app.main import create_app  # type: ignore[import-untyped]
    from httpx import AsyncClient
    from httpx._transports.asgi import ASGITransport

    from app.db.session import get_session

    app = create_app()

    async def _override() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_session] = _override

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client

    app.dependency_overrides.clear()
