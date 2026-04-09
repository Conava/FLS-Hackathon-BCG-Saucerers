"""Integration tests for pgvector HNSW index on ehr_record.embedding (T8).

Tests:
  1. test_hnsw_index_exists         — pg_indexes shows the HNSW index
  2. test_vector_extension_idempotent — CREATE EXTENSION IF NOT EXISTS vector twice is safe
  3. test_cosine_distance_query      — ORDER BY embedding <=> :qvec returns rows for a patient
"""

from __future__ import annotations

import math
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

import app.adapters.csv_source  # noqa: F401 — side-effect: registers @register("csv")
from app.ai.llm import FakeLLMProvider
from app.models import EHRRecord
from app.services.unified_profile import UnifiedProfileService

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"

# 768-d query vector to use for cosine-distance queries (all zeros except first)
_QUERY_VEC = [0.0] * 768
_QUERY_VEC[0] = 1.0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _ingest_with_embeddings(session: AsyncSession) -> None:
    """Run ingest against sample fixtures with FakeLLMProvider to populate embeddings."""
    llm = FakeLLMProvider()
    svc = UnifiedProfileService(session, llm_provider=llm)
    await svc.ingest("csv", data_dir=FIXTURES_DIR)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_hnsw_index_exists(engine: AsyncEngine) -> None:
    """The HNSW index ehr_record_embedding_hnsw must exist in pg_indexes.

    The create_all() function in app.db.base creates this index via raw DDL
    after the table schema is applied.  This test queries the pg_indexes view
    directly to verify the index is present and uses the expected access method.
    """
    async with engine.connect() as conn:
        result = await conn.execute(
            text(
                """
                SELECT indexname, indexdef
                FROM pg_indexes
                WHERE tablename = 'ehr_record'
                  AND indexname = 'ehr_record_embedding_hnsw'
                """
            )
        )
        rows = result.fetchall()

    assert len(rows) == 1, (
        f"Expected HNSW index 'ehr_record_embedding_hnsw' on table 'ehr_record' "
        f"but pg_indexes returned {len(rows)} rows: {rows}"
    )

    index_def = rows[0][1]
    assert "hnsw" in index_def.lower(), (
        f"Index exists but does not use HNSW access method. indexdef: {index_def}"
    )
    assert "vector_cosine_ops" in index_def, (
        f"Index exists but does not use vector_cosine_ops operator class. indexdef: {index_def}"
    )


@pytest.mark.integration
async def test_vector_extension_idempotent(engine: AsyncEngine) -> None:
    """CREATE EXTENSION IF NOT EXISTS vector can be called multiple times without error.

    This verifies the idempotency guarantee of the create_all() helper:
    running schema setup twice on an already-provisioned DB must not raise.
    """
    from app.db.base import create_all

    # If this raises, the idempotency contract is broken.
    await create_all(engine)
    await create_all(engine)


@pytest.mark.integration
async def test_cosine_distance_query(db_session: AsyncSession) -> None:
    """A cosine-distance query returns rows ordered by embedding proximity.

    After ingest with FakeLLMProvider (which populates deterministic 768-d
    embeddings), a ORDER BY embedding <=> :qvec LIMIT 1 query must return
    exactly one row that belongs to the queried patient.

    This exercises the pgvector <=> operator against the HNSW index end-to-end.
    """
    await _ingest_with_embeddings(db_session)

    # Build a pgvector-compatible string representation of the query vector
    qvec_str = "[" + ",".join(str(v) for v in _QUERY_VEC) + "]"

    result = await db_session.execute(
        text(
            """
            SELECT id, patient_id
            FROM ehr_record
            WHERE patient_id = :pid
            ORDER BY embedding <=> CAST(:qvec AS vector)
            LIMIT 1
            """
        ),
        {"pid": "PT0001", "qvec": qvec_str},
    )
    row = result.fetchone()

    assert row is not None, (
        "cosine-distance query returned no rows for PT0001 — "
        "embeddings may not have been populated"
    )
    assert row[1] == "PT0001", (
        f"cosine-distance query returned a row belonging to patient {row[1]!r}, "
        f"expected PT0001 — patient_id filter is broken"
    )


@pytest.mark.integration
async def test_cosine_distance_isolation(db_session: AsyncSession) -> None:
    """Cosine-distance query scoped to PT0001 never returns PT0282 rows.

    Hard isolation: the WHERE patient_id = :pid clause must be respected
    even when using vector ordering.  Every returned row must belong to
    the queried patient.
    """
    await _ingest_with_embeddings(db_session)

    qvec_str = "[" + ",".join(str(v) for v in _QUERY_VEC) + "]"

    result = await db_session.execute(
        text(
            """
            SELECT id, patient_id
            FROM ehr_record
            WHERE patient_id = :pid
            ORDER BY embedding <=> CAST(:qvec AS vector)
            LIMIT 10
            """
        ),
        {"pid": "PT0001", "qvec": qvec_str},
    )
    rows = result.fetchall()

    assert len(rows) > 0, "Expected at least one row for PT0001"
    for row in rows:
        assert row[1] == "PT0001", (
            f"ISOLATION BREACH: cosine query scoped to PT0001 returned row "
            f"id={row[0]} patient_id={row[1]!r}"
        )
