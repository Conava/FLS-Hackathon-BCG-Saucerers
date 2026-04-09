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


# ---------------------------------------------------------------------------
# Slice 2 cross-patient isolation assertions (T7)
# Seed two patients; query with one; assert the other's rows are invisible.
# ---------------------------------------------------------------------------


class TestSlice2ProtocolIsolation:
    """Protocol rows seeded for patient A must not be visible when querying as B."""

    async def test_protocol_cross_patient_isolation(
        self, session: AsyncSession
    ) -> None:
        import datetime

        from app.repositories.protocol_repo import ProtocolRepository

        import app.models  # noqa: F401

        patient_a = make_patient("PT_ISO_PR_A")
        patient_b = make_patient("PT_ISO_PR_B")
        session.add(patient_a)
        session.add(patient_b)
        await session.flush()

        repo = ProtocolRepository(session)
        p = app.models.Protocol(  # type: ignore[attr-defined]
            patient_id="PT_ISO_PR_A",
            week_start=datetime.date(2026, 4, 7),
            status="active",
        )
        await repo.create(patient_id="PT_ISO_PR_A", protocol=p)

        # Patient B must not see Patient A's protocol
        results = await repo.list(patient_id="PT_ISO_PR_B")
        assert results == [], "Protocol isolation violated: Patient B sees Patient A's data"


class TestSlice2DailyLogIsolation:
    """DailyLog rows seeded for patient A must not be visible when querying as B."""

    async def test_daily_log_cross_patient_isolation(
        self, session: AsyncSession
    ) -> None:
        import datetime

        from app.repositories.daily_log_repo import DailyLogRepository

        import app.models  # noqa: F401

        patient_a = make_patient("PT_ISO_DL_A")
        patient_b = make_patient("PT_ISO_DL_B")
        session.add(patient_a)
        session.add(patient_b)
        await session.flush()

        repo = DailyLogRepository(session)
        log = app.models.DailyLog(  # type: ignore[attr-defined]
            patient_id="PT_ISO_DL_A",
            logged_at=datetime.datetime(2026, 4, 9, 10, 0, 0),
            mood=5,
        )
        await repo.create(patient_id="PT_ISO_DL_A", log=log)

        # Patient B must not see Patient A's logs
        results = await repo.list_by_date_range(
            patient_id="PT_ISO_DL_B",
            from_dt=datetime.datetime(2026, 1, 1),
            to_dt=datetime.datetime(2026, 12, 31),
        )
        assert results == [], "DailyLog isolation violated: Patient B sees Patient A's data"


class TestSlice2MealLogIsolation:
    """MealLog rows seeded for patient A must not be visible when querying as B."""

    async def test_meal_log_cross_patient_isolation(
        self, session: AsyncSession
    ) -> None:
        import datetime

        from app.repositories.meal_log_repo import MealLogRepository

        import app.models  # noqa: F401

        patient_a = make_patient("PT_ISO_ML_A")
        patient_b = make_patient("PT_ISO_ML_B")
        session.add(patient_a)
        session.add(patient_b)
        await session.flush()

        repo = MealLogRepository(session)
        meal = app.models.MealLog(  # type: ignore[attr-defined]
            patient_id="PT_ISO_ML_A",
            photo_uri="local://test/iso.jpg",
            analyzed_at=datetime.datetime(2026, 4, 9, 10, 0, 0),
        )
        await repo.create(patient_id="PT_ISO_ML_A", meal=meal)

        # Patient B must not see Patient A's meals
        results = await repo.list_recent(patient_id="PT_ISO_ML_B", limit=100)
        assert results == [], "MealLog isolation violated: Patient B sees Patient A's data"


class TestSlice2SurveyIsolation:
    """SurveyResponse rows seeded for patient A must not be visible when querying as B."""

    async def test_survey_cross_patient_isolation(
        self, session: AsyncSession
    ) -> None:
        import datetime

        from app.repositories.survey_repo import SurveyRepository

        import app.models  # noqa: F401

        patient_a = make_patient("PT_ISO_SR_A")
        patient_b = make_patient("PT_ISO_SR_B")
        session.add(patient_a)
        session.add(patient_b)
        await session.flush()

        repo = SurveyRepository(session)
        s = app.models.SurveyResponse(  # type: ignore[attr-defined]
            patient_id="PT_ISO_SR_A",
            kind="weekly",
            answers={"energy": 4},
            submitted_at=datetime.datetime(2026, 4, 9, 10, 0, 0),
        )
        await repo.create(patient_id="PT_ISO_SR_A", survey=s)

        # Patient B must not see Patient A's surveys
        results = await repo.history(patient_id="PT_ISO_SR_B", kind="weekly")
        assert results == [], "Survey isolation violated: Patient B sees Patient A's data"

        latest = await repo.latest_by_kind(patient_id="PT_ISO_SR_B", kind="weekly")
        assert latest is None, "Survey latest_by_kind isolation violated"


class TestSlice2OutlookIsolation:
    """VitalityOutlook rows seeded for patient A must not be visible when querying as B."""

    async def test_outlook_cross_patient_isolation(
        self, session: AsyncSession
    ) -> None:
        import datetime

        from app.repositories.outlook_repo import VitalityOutlookRepository

        import app.models  # noqa: F401

        patient_a = make_patient("PT_ISO_VO_A")
        patient_b = make_patient("PT_ISO_VO_B")
        session.add(patient_a)
        session.add(patient_b)
        await session.flush()

        repo = VitalityOutlookRepository(session)
        o = app.models.VitalityOutlook(  # type: ignore[attr-defined]
            patient_id="PT_ISO_VO_A",
            horizon_months=3,
            projected_score=80.0,
            narrative="Great trajectory.",
            computed_at=datetime.datetime(2026, 4, 9, 10, 0, 0),
        )
        await repo.upsert_by_horizon(patient_id="PT_ISO_VO_A", outlook=o)

        # Patient B must not see Patient A's outlook
        latest = await repo.latest(patient_id="PT_ISO_VO_B", horizon_months=3)
        assert latest is None, "Outlook isolation violated: Patient B sees Patient A's data"


class TestSlice2MessageIsolation:
    """Message rows seeded for patient A must not be visible when querying as B."""

    async def test_message_cross_patient_isolation(
        self, session: AsyncSession
    ) -> None:
        from app.repositories.message_repo import MessageRepository

        import app.models  # noqa: F401

        patient_a = make_patient("PT_ISO_MSG_A")
        patient_b = make_patient("PT_ISO_MSG_B")
        session.add(patient_a)
        session.add(patient_b)
        await session.flush()

        repo = MessageRepository(session)
        msg = app.models.Message(  # type: ignore[attr-defined]
            patient_id="PT_ISO_MSG_A",
            sender="patient",
            content="Secret message",
        )
        await repo.create(patient_id="PT_ISO_MSG_A", message=msg)

        # Patient B must not see Patient A's messages
        results = await repo.list(patient_id="PT_ISO_MSG_B")
        assert results == [], "Message isolation violated: Patient B sees Patient A's data"


class TestSlice2NotificationIsolation:
    """Notification rows seeded for patient A must not be visible when querying as B."""

    async def test_notification_cross_patient_isolation(
        self, session: AsyncSession
    ) -> None:
        from app.repositories.notification_repo import NotificationRepository

        import app.models  # noqa: F401

        patient_a = make_patient("PT_ISO_NTF_A")
        patient_b = make_patient("PT_ISO_NTF_B")
        session.add(patient_a)
        session.add(patient_b)
        await session.flush()

        repo = NotificationRepository(session)
        notif = app.models.Notification(  # type: ignore[attr-defined]
            patient_id="PT_ISO_NTF_A",
            kind="nudge",
            title="Private nudge",
            body="For PT_A only",
        )
        await repo.create(patient_id="PT_ISO_NTF_A", notification=notif)

        # Patient B must not see Patient A's notifications
        results = await repo.list(patient_id="PT_ISO_NTF_B")
        assert results == [], "Notification isolation violated: Patient B sees Patient A's data"


class TestSlice2ClinicalReviewIsolation:
    """ClinicalReview rows seeded for patient A must not be visible when querying as B."""

    async def test_clinical_review_cross_patient_isolation(
        self, session: AsyncSession
    ) -> None:
        from app.repositories.clinical_review_repo import ClinicalReviewRepository

        import app.models  # noqa: F401

        patient_a = make_patient("PT_ISO_CR_A")
        patient_b = make_patient("PT_ISO_CR_B")
        session.add(patient_a)
        session.add(patient_b)
        await session.flush()

        repo = ClinicalReviewRepository(session)
        review = app.models.ClinicalReview(  # type: ignore[attr-defined]
            patient_id="PT_ISO_CR_A",
            reason="Sensitive review for A",
            status="pending",
        )
        await repo.create(patient_id="PT_ISO_CR_A", review=review)

        # Patient B must not see Patient A's reviews
        results = await repo.list(patient_id="PT_ISO_CR_B")
        assert results == [], "ClinicalReview isolation violated: Patient B sees Patient A's data"


class TestSlice2ReferralIsolation:
    """Referral rows seeded for patient A must not be visible when querying as B."""

    async def test_referral_cross_patient_isolation(
        self, session: AsyncSession
    ) -> None:
        from app.repositories.referral_repo import ReferralRepository

        import app.models  # noqa: F401

        patient_a = make_patient("PT_ISO_RF_A")
        patient_b = make_patient("PT_ISO_RF_B")
        session.add(patient_a)
        session.add(patient_b)
        await session.flush()

        repo = ReferralRepository(session)
        ref = app.models.Referral(  # type: ignore[attr-defined]
            patient_id="PT_ISO_RF_A",
            code="REF-ISO-AAAA",
            status="pending",
        )
        await repo.create(patient_id="PT_ISO_RF_A", referral=ref)

        # Patient B must not see Patient A's referrals
        results = await repo.list(patient_id="PT_ISO_RF_B")
        assert results == [], "Referral isolation violated: Patient B sees Patient A's data"


class TestSlice2ProtocolActionIsolation:
    """ProtocolAction rows for patient A must not be visible when querying as patient B.

    ProtocolAction has no patient_id column — isolation is enforced via a
    subquery: SELECT ... FROM protocol_action WHERE protocol_id IN
    (SELECT id FROM protocol WHERE patient_id = :pid).
    """

    async def test_protocol_action_cross_patient_isolation(
        self, session: AsyncSession
    ) -> None:
        import datetime

        from app.repositories.protocol_repo import (
            ProtocolActionRepository,
            ProtocolRepository,
        )

        import app.models  # noqa: F401

        patient_a = make_patient("PT_ISO_PA_A")
        patient_b = make_patient("PT_ISO_PA_B")
        session.add(patient_a)
        session.add(patient_b)
        await session.flush()

        proto_repo = ProtocolRepository(session)
        # Patient A gets a protocol with one action
        p = app.models.Protocol(  # type: ignore[attr-defined]
            patient_id="PT_ISO_PA_A",
            week_start=datetime.date(2026, 4, 7),
            status="active",
        )
        proto = await proto_repo.create(patient_id="PT_ISO_PA_A", protocol=p)
        assert proto.id is not None

        action_repo = ProtocolActionRepository(session)
        action = app.models.ProtocolAction(  # type: ignore[attr-defined]
            protocol_id=proto.id,
            category="movement",
            title="Patient A's secret action",
        )
        await action_repo.add(action=action)

        # Patient B queries — must get empty list (no protocols → no actions)
        results = await action_repo.list_for_patient(patient_id="PT_ISO_PA_B")
        assert results == [], (
            "ProtocolAction isolation violated: Patient B can see Patient A's actions"
        )
