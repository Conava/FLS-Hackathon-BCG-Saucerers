"""SQLModel metadata re-export and schema-creation helper.

This module provides:
* ``metadata`` — the shared ``sqlalchemy.MetaData`` instance that all SQLModel
  table models register themselves with.  Import this (not ``SQLModel.metadata``
  directly) so downstream code has a stable import path.
* ``create_all(engine)`` — convenience coroutine that creates all registered
  tables.  Intended for local dev and test fixtures; Alembic handles production
  migrations.

Note: importing this module is side-effect-free.  No DB connection is opened
at import time.
"""

from __future__ import annotations

from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlmodel import SQLModel

# Re-export the SQLModel metadata so the rest of the codebase has a single
# stable import target.  All SQLModel table models auto-register here.
metadata: MetaData = SQLModel.metadata


async def create_all(engine: AsyncEngine) -> None:
    """Create all SQLModel-registered tables in the target database.

    This is a convenience wrapper around ``SQLModel.metadata.create_all`` for
    async engines.  It is **not** idempotent in the Alembic sense — it issues
    ``CREATE TABLE IF NOT EXISTS`` so repeated calls on an existing schema are
    safe but won't apply column changes.

    Before creating tables, this installs the ``vector`` extension
    (``CREATE EXTENSION IF NOT EXISTS vector``) in the same transaction so
    that the ``pgvector`` ``Vector`` column type is always available — even
    on a freshly provisioned Cloud SQL instance.

    After creating tables, this also creates an HNSW index on
    ``ehr_record.embedding`` using the ``vector_cosine_ops`` operator class.
    This index DDL is non-standard and cannot be expressed via SQLModel/SQLAlchemy
    ORM, so it is issued as raw SQL.  The ``IF NOT EXISTS`` guard makes repeated
    calls idempotent.

    Args:
        engine: The ``AsyncEngine`` to run DDL against.  Typically obtained via
            ``app.db.session.get_engine()``.

    Usage::

        from app.db.session import get_engine
        from app.db.base import create_all

        engine = get_engine()
        await create_all(engine)
    """
    async with engine.begin() as conn:
        await conn.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS vector")
        await conn.run_sync(SQLModel.metadata.create_all)
        # HNSW index on ehr_record.embedding — non-standard DDL, cannot be
        # expressed via SQLModel/SQLAlchemy ORM, so we use raw SQL.
        # IF NOT EXISTS makes repeated calls idempotent.
        await conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS ehr_record_embedding_hnsw "
            "ON ehr_record USING hnsw (embedding vector_cosine_ops)"
        )
