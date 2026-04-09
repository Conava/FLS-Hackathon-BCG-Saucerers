"""Integration tests for Slice 2 repositories.

Round-trip write/read tests for every new repository. Uses the shared
``db_session`` fixture from tests/conftest.py (testcontainers Postgres 16
+ pgvector, per-test rollback).

Stack: SQLAlchemy 2.0 async + SQLModel + Postgres 16 + pgvector.
"""

from __future__ import annotations

import datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

import app.models  # noqa: F401 — side-effect import registers all tables


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------


def _dt(year: int = 2026, month: int = 4, day: int = 9) -> datetime.datetime:
    """Return a naive UTC datetime."""
    return datetime.datetime(year, month, day, 10, 0, 0)


def make_patient(patient_id: str) -> app.models.Patient:  # type: ignore[name-defined]
    return app.models.Patient(  # type: ignore[attr-defined]
        patient_id=patient_id,
        name=f"Test {patient_id}",
        age=35,
        sex="unknown",
        country="DE",
    )


# ---------------------------------------------------------------------------
# ProtocolRepository + ProtocolActionRepository
# ---------------------------------------------------------------------------


class TestProtocolRepository:
    """Round-trip tests for ProtocolRepository."""

    async def test_create_and_get_protocol(self, db_session: AsyncSession) -> None:
        """create() persists a Protocol; get() retrieves it by patient+id."""
        from app.repositories.protocol_repo import ProtocolRepository

        db_session.add(make_patient("PT_PR001"))
        await db_session.flush()

        repo = ProtocolRepository(db_session)
        protocol = app.models.Protocol(  # type: ignore[attr-defined]
            patient_id="PT_PR001",
            week_start=datetime.date(2026, 4, 7),
            status="active",
        )
        created = await repo.create(patient_id="PT_PR001", protocol=protocol)

        assert created.id is not None
        fetched = await repo.get(patient_id="PT_PR001", record_id=created.id)
        assert fetched is not None
        assert fetched.patient_id == "PT_PR001"
        assert fetched.status == "active"

    async def test_list_protocols_for_patient(self, db_session: AsyncSession) -> None:
        """list() returns all protocols for a patient."""
        from app.repositories.protocol_repo import ProtocolRepository

        db_session.add(make_patient("PT_PR002"))
        await db_session.flush()

        repo = ProtocolRepository(db_session)
        for status in ("active", "completed"):
            p = app.models.Protocol(  # type: ignore[attr-defined]
                patient_id="PT_PR002",
                week_start=datetime.date(2026, 4, 7),
                status=status,
            )
            await repo.create(patient_id="PT_PR002", protocol=p)

        results = await repo.list(patient_id="PT_PR002")
        assert len(results) >= 2
        assert all(r.patient_id == "PT_PR002" for r in results)

    async def test_get_active_protocol(self, db_session: AsyncSession) -> None:
        """get_active() returns the current active protocol for a patient."""
        from app.repositories.protocol_repo import ProtocolRepository

        db_session.add(make_patient("PT_PR003"))
        await db_session.flush()

        repo = ProtocolRepository(db_session)
        p = app.models.Protocol(  # type: ignore[attr-defined]
            patient_id="PT_PR003",
            week_start=datetime.date(2026, 4, 7),
            status="active",
        )
        created = await repo.create(patient_id="PT_PR003", protocol=p)

        active = await repo.get_active(patient_id="PT_PR003")
        assert active is not None
        assert active.id == created.id


class TestProtocolActionRepository:
    """Round-trip tests for ProtocolActionRepository.

    All queries go through a patient-scoped Protocol lookup — never a bare
    protocol_id without first confirming the protocol belongs to the patient.
    """

    async def test_add_and_list_actions_for_patient(
        self, db_session: AsyncSession
    ) -> None:
        """add() persists an action; list_for_patient() returns it."""
        from app.repositories.protocol_repo import (
            ProtocolActionRepository,
            ProtocolRepository,
        )

        db_session.add(make_patient("PT_PA001"))
        await db_session.flush()

        proto_repo = ProtocolRepository(db_session)
        p = app.models.Protocol(  # type: ignore[attr-defined]
            patient_id="PT_PA001",
            week_start=datetime.date(2026, 4, 7),
            status="active",
        )
        proto = await proto_repo.create(patient_id="PT_PA001", protocol=p)
        assert proto.id is not None

        action_repo = ProtocolActionRepository(db_session)
        action = app.models.ProtocolAction(  # type: ignore[attr-defined]
            protocol_id=proto.id,
            category="movement",
            title="Walk 30 minutes",
        )
        await action_repo.add(action=action)

        actions = await action_repo.list_for_patient(patient_id="PT_PA001")
        assert len(actions) >= 1
        assert all(a.category == "movement" for a in actions if a.protocol_id == proto.id)

    async def test_update_action_streak(self, db_session: AsyncSession) -> None:
        """update_streak() increments streak_days and sets completed_today."""
        from app.repositories.protocol_repo import (
            ProtocolActionRepository,
            ProtocolRepository,
        )

        db_session.add(make_patient("PT_PA002"))
        await db_session.flush()

        proto_repo = ProtocolRepository(db_session)
        p = app.models.Protocol(  # type: ignore[attr-defined]
            patient_id="PT_PA002",
            week_start=datetime.date(2026, 4, 7),
            status="active",
        )
        proto = await proto_repo.create(patient_id="PT_PA002", protocol=p)
        assert proto.id is not None

        action_repo = ProtocolActionRepository(db_session)
        action = app.models.ProtocolAction(  # type: ignore[attr-defined]
            protocol_id=proto.id,
            category="sleep",
            title="Lights out by 22:30",
        )
        created = await action_repo.add(action=action)
        assert created.id is not None

        updated = await action_repo.update_streak(
            patient_id="PT_PA002",
            action_id=created.id,
            streak_days=3,
            completed_today=True,
        )
        assert updated is not None
        assert updated.streak_days == 3
        assert updated.completed_today is True


# ---------------------------------------------------------------------------
# DailyLogRepository
# ---------------------------------------------------------------------------


class TestDailyLogRepository:
    """Round-trip tests for DailyLogRepository."""

    async def test_create_and_get_daily_log(self, db_session: AsyncSession) -> None:
        """create() persists a DailyLog; get() retrieves it."""
        from app.repositories.daily_log_repo import DailyLogRepository

        db_session.add(make_patient("PT_DL001"))
        await db_session.flush()

        repo = DailyLogRepository(db_session)
        log = app.models.DailyLog(  # type: ignore[attr-defined]
            patient_id="PT_DL001",
            logged_at=_dt(),
            mood=4,
            workout_minutes=30,
        )
        created = await repo.create(patient_id="PT_DL001", log=log)
        assert created.id is not None

        fetched = await repo.get(patient_id="PT_DL001", record_id=created.id)
        assert fetched is not None
        assert fetched.mood == 4
        assert fetched.patient_id == "PT_DL001"

    async def test_list_by_date_range(self, db_session: AsyncSession) -> None:
        """list_by_date_range() returns logs within the given date window."""
        from app.repositories.daily_log_repo import DailyLogRepository

        db_session.add(make_patient("PT_DL002"))
        await db_session.flush()

        repo = DailyLogRepository(db_session)
        in_range = app.models.DailyLog(  # type: ignore[attr-defined]
            patient_id="PT_DL002",
            logged_at=datetime.datetime(2026, 4, 5, 10, 0, 0),
            mood=3,
        )
        out_of_range = app.models.DailyLog(  # type: ignore[attr-defined]
            patient_id="PT_DL002",
            logged_at=datetime.datetime(2026, 3, 1, 10, 0, 0),
            mood=5,
        )
        await repo.create(patient_id="PT_DL002", log=in_range)
        await repo.create(patient_id="PT_DL002", log=out_of_range)

        results = await repo.list_by_date_range(
            patient_id="PT_DL002",
            from_dt=datetime.datetime(2026, 4, 1, 0, 0, 0),
            to_dt=datetime.datetime(2026, 4, 9, 23, 59, 59),
        )
        assert len(results) == 1
        assert results[0].mood == 3


# ---------------------------------------------------------------------------
# MealLogRepository
# ---------------------------------------------------------------------------


class TestMealLogRepository:
    """Round-trip tests for MealLogRepository."""

    async def test_create_and_get_meal_log(self, db_session: AsyncSession) -> None:
        """create() persists a MealLog; get() retrieves it by patient+id."""
        from app.repositories.meal_log_repo import MealLogRepository

        db_session.add(make_patient("PT_ML001"))
        await db_session.flush()

        repo = MealLogRepository(db_session)
        meal = app.models.MealLog(  # type: ignore[attr-defined]
            patient_id="PT_ML001",
            photo_uri="local://test/photo.jpg",
            analyzed_at=_dt(),
        )
        created = await repo.create(patient_id="PT_ML001", meal=meal)
        assert created.id is not None

        fetched = await repo.get(patient_id="PT_ML001", record_id=created.id)
        assert fetched is not None
        assert fetched.photo_uri == "local://test/photo.jpg"

    async def test_list_recent(self, db_session: AsyncSession) -> None:
        """list_recent() returns the most recent meal logs for a patient."""
        from app.repositories.meal_log_repo import MealLogRepository

        db_session.add(make_patient("PT_ML002"))
        await db_session.flush()

        repo = MealLogRepository(db_session)
        for i in range(3):
            m = app.models.MealLog(  # type: ignore[attr-defined]
                patient_id="PT_ML002",
                photo_uri=f"local://test/photo_{i}.jpg",
                analyzed_at=datetime.datetime(2026, 4, i + 1, 10, 0, 0),
            )
            await repo.create(patient_id="PT_ML002", meal=m)

        results = await repo.list_recent(patient_id="PT_ML002", limit=2)
        assert len(results) == 2
        # Newest first
        assert results[0].analyzed_at > results[1].analyzed_at

    async def test_delete_for_patient(self, db_session: AsyncSession) -> None:
        """delete_for_patient() removes all meal logs for a patient (GDPR)."""
        from app.repositories.meal_log_repo import MealLogRepository

        db_session.add(make_patient("PT_ML003"))
        await db_session.flush()

        repo = MealLogRepository(db_session)
        for i in range(2):
            m = app.models.MealLog(  # type: ignore[attr-defined]
                patient_id="PT_ML003",
                photo_uri=f"local://test/gdpr_{i}.jpg",
                analyzed_at=_dt(),
            )
            await repo.create(patient_id="PT_ML003", meal=m)

        await repo.delete_for_patient(patient_id="PT_ML003")
        remaining = await repo.list_recent(patient_id="PT_ML003", limit=100)
        assert remaining == []


# ---------------------------------------------------------------------------
# SurveyRepository
# ---------------------------------------------------------------------------


class TestSurveyRepository:
    """Round-trip tests for SurveyRepository."""

    async def test_create_and_latest_by_kind(self, db_session: AsyncSession) -> None:
        """create() persists a survey; latest_by_kind() retrieves the newest."""
        from app.repositories.survey_repo import SurveyRepository

        db_session.add(make_patient("PT_SR001"))
        await db_session.flush()

        repo = SurveyRepository(db_session)
        s = app.models.SurveyResponse(  # type: ignore[attr-defined]
            patient_id="PT_SR001",
            kind="onboarding",
            answers={"goal": "energy", "sleep_hours": 7},
            submitted_at=_dt(),
        )
        created = await repo.create(patient_id="PT_SR001", survey=s)
        assert created.id is not None

        latest = await repo.latest_by_kind(patient_id="PT_SR001", kind="onboarding")
        assert latest is not None
        assert latest.kind == "onboarding"
        assert latest.answers.get("goal") == "energy"

    async def test_history_returns_all_by_kind(self, db_session: AsyncSession) -> None:
        """history() returns all surveys for a patient filtered by kind."""
        from app.repositories.survey_repo import SurveyRepository

        db_session.add(make_patient("PT_SR002"))
        await db_session.flush()

        repo = SurveyRepository(db_session)
        for i in range(2):
            s = app.models.SurveyResponse(  # type: ignore[attr-defined]
                patient_id="PT_SR002",
                kind="weekly",
                answers={"energy": i + 1},
                submitted_at=datetime.datetime(2026, 4, i + 1, 10, 0, 0),
            )
            await repo.create(patient_id="PT_SR002", survey=s)

        results = await repo.history(patient_id="PT_SR002", kind="weekly")
        assert len(results) == 2
        assert all(r.kind == "weekly" for r in results)


# ---------------------------------------------------------------------------
# VitalityOutlookRepository
# ---------------------------------------------------------------------------


class TestVitalityOutlookRepository:
    """Round-trip tests for VitalityOutlookRepository."""

    async def test_upsert_creates_and_updates(self, db_session: AsyncSession) -> None:
        """upsert_by_horizon() creates; calling again updates in place."""
        from app.repositories.outlook_repo import VitalityOutlookRepository

        db_session.add(make_patient("PT_VO001"))
        await db_session.flush()

        repo = VitalityOutlookRepository(db_session)
        outlook = app.models.VitalityOutlook(  # type: ignore[attr-defined]
            patient_id="PT_VO001",
            horizon_months=3,
            projected_score=75.0,
            narrative="Looking good.",
            computed_at=_dt(),
        )
        created = await repo.upsert_by_horizon(patient_id="PT_VO001", outlook=outlook)
        assert created.id is not None
        assert created.projected_score == pytest.approx(75.0)

        # Update it
        updated_outlook = app.models.VitalityOutlook(  # type: ignore[attr-defined]
            patient_id="PT_VO001",
            horizon_months=3,
            projected_score=80.0,
            narrative="Even better.",
            computed_at=_dt(month=5),
        )
        updated = await repo.upsert_by_horizon(
            patient_id="PT_VO001", outlook=updated_outlook
        )
        assert updated.projected_score == pytest.approx(80.0)

    async def test_latest_returns_most_recent_per_horizon(
        self, db_session: AsyncSession
    ) -> None:
        """latest() returns the most recently computed outlook for a horizon."""
        from app.repositories.outlook_repo import VitalityOutlookRepository

        db_session.add(make_patient("PT_VO002"))
        await db_session.flush()

        repo = VitalityOutlookRepository(db_session)
        for score, month in [(60.0, 1), (70.0, 2)]:
            o = app.models.VitalityOutlook(  # type: ignore[attr-defined]
                patient_id="PT_VO002",
                horizon_months=6,
                projected_score=score,
                narrative="test",
                computed_at=datetime.datetime(2026, month, 1, 10, 0, 0),
            )
            await repo.upsert_by_horizon(patient_id="PT_VO002", outlook=o)

        latest = await repo.latest(patient_id="PT_VO002", horizon_months=6)
        assert latest is not None
        assert latest.projected_score == pytest.approx(70.0)


# ---------------------------------------------------------------------------
# MessageRepository
# ---------------------------------------------------------------------------


class TestMessageRepository:
    """Round-trip tests for MessageRepository."""

    async def test_create_and_list_messages(self, db_session: AsyncSession) -> None:
        """create() persists a message; list() returns it."""
        from app.repositories.message_repo import MessageRepository

        db_session.add(make_patient("PT_MSG001"))
        await db_session.flush()

        repo = MessageRepository(db_session)
        msg = app.models.Message(  # type: ignore[attr-defined]
            patient_id="PT_MSG001",
            sender="patient",
            content="Hello, how are my results?",
        )
        created = await repo.create(patient_id="PT_MSG001", message=msg)
        assert created.id is not None

        messages = await repo.list(patient_id="PT_MSG001")
        assert len(messages) >= 1
        assert any(m.content == "Hello, how are my results?" for m in messages)

    async def test_get_message_by_id(self, db_session: AsyncSession) -> None:
        """get() retrieves a specific message by id, scoped to patient."""
        from app.repositories.message_repo import MessageRepository

        db_session.add(make_patient("PT_MSG002"))
        await db_session.flush()

        repo = MessageRepository(db_session)
        msg = app.models.Message(  # type: ignore[attr-defined]
            patient_id="PT_MSG002",
            sender="clinician",
            content="Your results are in.",
        )
        created = await repo.create(patient_id="PT_MSG002", message=msg)
        assert created.id is not None

        fetched = await repo.get(patient_id="PT_MSG002", record_id=created.id)
        assert fetched is not None
        assert fetched.sender == "clinician"


# ---------------------------------------------------------------------------
# NotificationRepository
# ---------------------------------------------------------------------------


class TestNotificationRepository:
    """Round-trip tests for NotificationRepository."""

    async def test_create_and_list_notifications(
        self, db_session: AsyncSession
    ) -> None:
        """create() persists a notification; list() returns it."""
        from app.repositories.notification_repo import NotificationRepository

        db_session.add(make_patient("PT_NTF001"))
        await db_session.flush()

        repo = NotificationRepository(db_session)
        notif = app.models.Notification(  # type: ignore[attr-defined]
            patient_id="PT_NTF001",
            kind="nudge",
            title="Time to move!",
            body="You haven't logged a workout today.",
        )
        created = await repo.create(patient_id="PT_NTF001", notification=notif)
        assert created.id is not None

        results = await repo.list(patient_id="PT_NTF001")
        assert any(n.title == "Time to move!" for n in results)

    async def test_mark_read(self, db_session: AsyncSession) -> None:
        """mark_read() sets read_at on a notification for the correct patient."""
        from app.repositories.notification_repo import NotificationRepository

        db_session.add(make_patient("PT_NTF002"))
        await db_session.flush()

        repo = NotificationRepository(db_session)
        notif = app.models.Notification(  # type: ignore[attr-defined]
            patient_id="PT_NTF002",
            kind="insight",
            title="New insight available",
            body="Check your vitality score.",
        )
        created = await repo.create(patient_id="PT_NTF002", notification=notif)
        assert created.id is not None

        updated = await repo.mark_read(
            patient_id="PT_NTF002", notification_id=created.id
        )
        assert updated is not None
        assert updated.read_at is not None


# ---------------------------------------------------------------------------
# ClinicalReviewRepository
# ---------------------------------------------------------------------------


class TestClinicalReviewRepository:
    """Round-trip tests for ClinicalReviewRepository."""

    async def test_create_and_get_review(self, db_session: AsyncSession) -> None:
        """create() persists a ClinicalReview; get() retrieves it."""
        from app.repositories.clinical_review_repo import ClinicalReviewRepository

        db_session.add(make_patient("PT_CR001"))
        await db_session.flush()

        repo = ClinicalReviewRepository(db_session)
        review = app.models.ClinicalReview(  # type: ignore[attr-defined]
            patient_id="PT_CR001",
            reason="Elevated biomarker detected",
            status="pending",
        )
        created = await repo.create(patient_id="PT_CR001", review=review)
        assert created.id is not None

        fetched = await repo.get(patient_id="PT_CR001", record_id=created.id)
        assert fetched is not None
        assert fetched.reason == "Elevated biomarker detected"
        assert fetched.status == "pending"

    async def test_list_reviews(self, db_session: AsyncSession) -> None:
        """list() returns all reviews for a patient."""
        from app.repositories.clinical_review_repo import ClinicalReviewRepository

        db_session.add(make_patient("PT_CR002"))
        await db_session.flush()

        repo = ClinicalReviewRepository(db_session)
        for status in ("pending", "in_review"):
            r = app.models.ClinicalReview(  # type: ignore[attr-defined]
                patient_id="PT_CR002",
                reason="Some reason",
                status=status,
            )
            await repo.create(patient_id="PT_CR002", review=r)

        results = await repo.list(patient_id="PT_CR002")
        assert len(results) >= 2
        assert all(r.patient_id == "PT_CR002" for r in results)


# ---------------------------------------------------------------------------
# ReferralRepository
# ---------------------------------------------------------------------------


class TestReferralRepository:
    """Round-trip tests for ReferralRepository."""

    async def test_create_and_get_referral(self, db_session: AsyncSession) -> None:
        """create() persists a Referral; get() retrieves it."""
        from app.repositories.referral_repo import ReferralRepository

        db_session.add(make_patient("PT_RF001"))
        await db_session.flush()

        repo = ReferralRepository(db_session)
        ref = app.models.Referral(  # type: ignore[attr-defined]
            patient_id="PT_RF001",
            code="REF-ABCD-0001",
            status="pending",
        )
        created = await repo.create(patient_id="PT_RF001", referral=ref)
        assert created.id is not None

        fetched = await repo.get(patient_id="PT_RF001", record_id=created.id)
        assert fetched is not None
        assert fetched.code == "REF-ABCD-0001"

    async def test_get_by_code(self, db_session: AsyncSession) -> None:
        """get_by_code() retrieves a referral by code, scoped to patient."""
        from app.repositories.referral_repo import ReferralRepository

        db_session.add(make_patient("PT_RF002"))
        await db_session.flush()

        repo = ReferralRepository(db_session)
        ref = app.models.Referral(  # type: ignore[attr-defined]
            patient_id="PT_RF002",
            code="REF-XYZ-9999",
            status="pending",
        )
        await repo.create(patient_id="PT_RF002", referral=ref)

        found = await repo.get_by_code(patient_id="PT_RF002", code="REF-XYZ-9999")
        assert found is not None
        assert found.patient_id == "PT_RF002"

        # Code for wrong patient returns None
        not_found = await repo.get_by_code(
            patient_id="PT_WRONG", code="REF-XYZ-9999"
        )
        assert not_found is None
