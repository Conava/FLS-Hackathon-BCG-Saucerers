"""Integration tests for PatientScopedRepository — hard patient_id isolation.

These tests prove that the GDPR hard-isolation invariant holds:
every SQL query filters by patient_id at the SQL level; querying with the
wrong patient_id returns None / empty list, not a cross-patient data leak.

The inline `engine` fixture spins up a real Postgres 16 + pgvector container
so the tests are self-contained and do not depend on T9's conftest.
T9's `db_session` fixture will supersede this inline fixture once merged.
"""

from __future__ import annotations

import datetime
from typing import Any

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlmodel import SQLModel
from testcontainers.postgres import PostgresContainer

import app.models  # noqa: F401 — side effect: registers all SQLModel tables
from app.models import EHRRecord

# ---------------------------------------------------------------------------
# Inline testcontainers fixture (self-contained, superseded by T9 conftest)
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="module")
async def engine():  # type: ignore[return]
    """Session-scoped Postgres+pgvector container with schema created."""
    with PostgresContainer("pgvector/pgvector:pg16") as pg:
        raw_url = pg.get_connection_url()
        # testcontainers returns psycopg2 URL; we need asyncpg
        # Normalise to postgresql+asyncpg:// regardless of what testcontainers emits
        async_url = raw_url
        if "+asyncpg" not in async_url:
            async_url = async_url.replace("psycopg2", "asyncpg")
        if async_url.startswith("postgresql://"):
            async_url = "postgresql+asyncpg://" + async_url[len("postgresql://"):]
        elif async_url.startswith("postgresql+psycopg2://"):
            async_url = "postgresql+asyncpg://" + async_url[len("postgresql+psycopg2://"):]

        eng = create_async_engine(async_url, echo=False)
        async with eng.begin() as conn:
            await conn.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS vector")
            await conn.run_sync(SQLModel.metadata.create_all)
        yield eng
        await eng.dispose()


@pytest_asyncio.fixture
async def session(engine: Any) -> Any:  # type: ignore[return]
    """Function-scoped session with rollback after each test."""
    async with AsyncSession(engine, expire_on_commit=False) as s:
        yield s
        await s.rollback()


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------


def make_patient(patient_id: str) -> app.models.Patient:  # type: ignore[name-defined]
    """Build a minimal Patient instance."""
    return app.models.Patient(  # type: ignore[attr-defined]
        patient_id=patient_id,
        name=f"Test {patient_id}",
        age=40,
        sex="unknown",
        country="DE",
    )


def make_ehr_record(patient_id: str, record_type: str = "visit") -> app.models.EHRRecord:  # type: ignore[name-defined]
    """Build a minimal EHRRecord instance."""
    return app.models.EHRRecord(  # type: ignore[attr-defined]
        patient_id=patient_id,
        record_type=record_type,
        recorded_at=datetime.datetime(2026, 1, 1, 0, 0, 0),  # naive UTC — matches TIMESTAMP WITHOUT TIME ZONE
        payload={"date": "2026-01-01"},
        source="test",
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestGetByIdWrongPatientReturnsNone:
    """get() must return None when patient_id doesn't match the record owner."""

    async def test_get_by_id_wrong_patient_returns_none(self, session: AsyncSession) -> None:
        from app.repositories.base import PatientScopedRepository

        # Insert patient PT0001 and a record belonging to them
        patient = make_patient("PT0001")
        session.add(patient)
        await session.flush()

        record = make_ehr_record("PT0001")
        session.add(record)
        await session.flush()
        assert record.id is not None

        repo: PatientScopedRepository[EHRRecord] = PatientScopedRepository(
            session=session, model=EHRRecord
        )

        # Query the record's id but under a DIFFERENT patient_id — must return None
        result = await repo.get(patient_id="PT0282", record_id=record.id)
        assert result is None, (
            "Cross-patient read must return None — GDPR isolation violated"
        )

    async def test_get_by_id_correct_patient_returns_record(self, session: AsyncSession) -> None:
        from app.repositories.base import PatientScopedRepository

        patient = make_patient("PT0002")
        session.add(patient)
        await session.flush()

        record = make_ehr_record("PT0002")
        session.add(record)
        await session.flush()
        assert record.id is not None

        repo: PatientScopedRepository[EHRRecord] = PatientScopedRepository(
            session=session, model=EHRRecord
        )

        result = await repo.get(patient_id="PT0002", record_id=record.id)
        assert result is not None
        assert result.patient_id == "PT0002"


class TestListWrongPatientReturnsEmpty:
    """list() must return [] when patient_id doesn't match any records."""

    async def test_list_wrong_patient_returns_empty(self, session: AsyncSession) -> None:
        from app.repositories.base import PatientScopedRepository

        patient = make_patient("PT0003")
        session.add(patient)
        await session.flush()

        # Insert 2 records for PT0003
        session.add(make_ehr_record("PT0003", "condition"))
        session.add(make_ehr_record("PT0003", "medication"))
        await session.flush()

        repo: PatientScopedRepository[EHRRecord] = PatientScopedRepository(
            session=session, model=EHRRecord
        )

        # Query with a different patient — must get empty list
        results = await repo.list(patient_id="PT9999")
        assert results == [], (
            "Cross-patient list must return [] — GDPR isolation violated"
        )

    async def test_list_correct_patient_returns_records(self, session: AsyncSession) -> None:
        from app.repositories.base import PatientScopedRepository

        patient = make_patient("PT0004")
        session.add(patient)
        await session.flush()

        session.add(make_ehr_record("PT0004", "condition"))
        session.add(make_ehr_record("PT0004", "medication"))
        await session.flush()

        repo: PatientScopedRepository[EHRRecord] = PatientScopedRepository(
            session=session, model=EHRRecord
        )

        results = await repo.list(patient_id="PT0004")
        assert len(results) == 2
        assert all(r.patient_id == "PT0004" for r in results)


class TestUpsertSetsPatientId:
    """upsert() must set patient_id on the object before persisting."""

    async def test_upsert_sets_patient_id_even_if_omitted_on_obj(
        self, session: AsyncSession
    ) -> None:
        from app.repositories.base import PatientScopedRepository

        patient = make_patient("PT0005")
        session.add(patient)
        await session.flush()

        # Create a record WITHOUT setting patient_id (intentionally wrong / missing)
        record = app.models.EHRRecord(  # type: ignore[attr-defined]
            patient_id="WRONG_INITIAL",  # will be overwritten by upsert
            record_type="visit",
            recorded_at=datetime.datetime(2026, 1, 2, 0, 0, 0),  # naive UTC — matches TIMESTAMP WITHOUT TIME ZONE
            payload={"date": "2026-01-02"},
            source="test",
        )

        repo: PatientScopedRepository[EHRRecord] = PatientScopedRepository(
            session=session, model=EHRRecord
        )

        # upsert with the correct patient_id — the repo must overwrite whatever was set
        merged = await repo.upsert(patient_id="PT0005", obj=record)
        assert merged.patient_id == "PT0005", (
            "upsert() must defensively set patient_id before persisting"
        )

    async def test_upsert_persists_and_returns_merged_instance(
        self, session: AsyncSession
    ) -> None:
        from app.repositories.base import PatientScopedRepository

        patient = make_patient("PT0006")
        session.add(patient)
        await session.flush()

        record = make_ehr_record("PT0006", "lab_panel")
        repo: PatientScopedRepository[EHRRecord] = PatientScopedRepository(
            session=session, model=EHRRecord
        )

        merged = await repo.upsert(patient_id="PT0006", obj=record)
        assert merged is not None
        assert merged.patient_id == "PT0006"


class TestListRespectsAdditionalFiltersWithIsolation:
    """list() with extra kwargs filters by those columns AND enforces patient_id isolation."""

    async def test_list_respects_additional_filters_with_isolation(
        self, session: AsyncSession
    ) -> None:
        from app.repositories.base import PatientScopedRepository

        patient_a = make_patient("PT0007")
        patient_b = make_patient("PT0008")
        session.add(patient_a)
        session.add(patient_b)
        await session.flush()

        # PT0007 has both a condition and a visit
        session.add(make_ehr_record("PT0007", "condition"))
        session.add(make_ehr_record("PT0007", "visit"))
        # PT0008 also has a condition
        session.add(make_ehr_record("PT0008", "condition"))
        await session.flush()

        repo: PatientScopedRepository[EHRRecord] = PatientScopedRepository(
            session=session, model=EHRRecord
        )

        # Filter by record_type="condition" for PT0007 — should return 1 row
        results = await repo.list(patient_id="PT0007", record_type="condition")
        assert len(results) == 1
        assert results[0].patient_id == "PT0007"
        assert results[0].record_type == "condition"

    async def test_list_filters_do_not_leak_other_patients(
        self, session: AsyncSession
    ) -> None:
        from app.repositories.base import PatientScopedRepository

        patient_c = make_patient("PT0009")
        patient_d = make_patient("PT0010")
        session.add(patient_c)
        session.add(patient_d)
        await session.flush()

        # PT0009 has a condition, PT0010 also has a condition
        session.add(make_ehr_record("PT0009", "condition"))
        session.add(make_ehr_record("PT0010", "condition"))
        await session.flush()

        repo: PatientScopedRepository[EHRRecord] = PatientScopedRepository(
            session=session, model=EHRRecord
        )

        # Filter record_type="condition" for PT0009 must NOT return PT0010's condition
        results = await repo.list(patient_id="PT0009", record_type="condition")
        assert all(r.patient_id == "PT0009" for r in results), (
            "list() with filters must not leak records from other patients"
        )
