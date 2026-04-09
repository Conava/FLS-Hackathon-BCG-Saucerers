"""
Compose smoke test — verifies that the local docker-compose stack has Postgres 16
with the pgvector extension available.

Marked @pytest.mark.compose so it is SKIPPED in CI by default.
Run locally after `docker compose up -d db`:

    cd backend
    uv run pytest tests/integration/test_compose_smoke.py -m compose -v

The DATABASE_URL environment variable must point to the running db service.
Default (matches docker-compose.yml): postgresql+asyncpg://postgres:postgres@localhost:5432/longevity
"""

import os

import pytest

# Lazy import inside the test function so collection does not fail when T1's
# pyproject.toml / app package is not yet present in the working tree.


pytestmark = pytest.mark.compose


@pytest.mark.asyncio
async def test_pgvector_available() -> None:
    """Connect to DATABASE_URL, enable vector extension, and execute a vector literal."""
    # Lazy imports — keeps the module importable before T1's pyproject is merged.
    try:
        import sqlalchemy  # noqa: F401
    except ImportError:
        pytest.skip("sqlalchemy not installed — run `uv sync` first")

    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    database_url = os.environ.get(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/longevity",
    )

    engine = create_async_engine(database_url, echo=False)
    try:
        async with engine.begin() as conn:
            # Enable pgvector (idempotent)
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))

            # Verify the extension is functional by casting a vector literal
            result = await conn.execute(text("SELECT '[1,2,3]'::vector;"))
            row = result.fetchone()
            assert row is not None, "Expected a result row from vector cast"
            # The value comes back as a string representation of the vector
            assert row[0] is not None, "Vector cast returned NULL"
    finally:
        await engine.dispose()
