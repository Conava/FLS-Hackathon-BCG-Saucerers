"""Integration tests for T14 stub services.

Tests for NotificationsService, ClinicalReviewService, ReferralService,
and MessagesService.

Each service class has two tests:
  1. Write/read round-trip — creates a row and retrieves it.
  2. Cross-patient isolation — rows created for patient A are invisible to patient B.

Uses the shared ``db_session`` fixture (testcontainers Postgres 16 + pgvector,
per-test rollback).

Stack: SQLAlchemy 2.0 async + SQLModel + Postgres 16.
"""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

import app.models  # noqa: F401 — side-effect import registers all tables


# ---------------------------------------------------------------------------
# Patient helper
# ---------------------------------------------------------------------------


def _make_patient(patient_id: str) -> app.models.Patient:  # type: ignore[name-defined]
    """Create a minimal Patient fixture for FK satisfaction."""
    return app.models.Patient(  # type: ignore[attr-defined]
        patient_id=patient_id,
        name=f"Test {patient_id}",
        age=40,
        sex="unknown",
        country="DE",
    )


# ---------------------------------------------------------------------------
# TestNotificationsService
# ---------------------------------------------------------------------------


class TestNotificationsService:
    """Round-trip + isolation tests for NotificationsService."""

    async def test_generate_smart_creates_row_and_returns_response(
        self, db_session: AsyncSession
    ) -> None:
        """generate_smart() persists a Notification and returns SmartNotificationResponse."""
        from app.ai.llm import FakeLLMProvider
        from app.services.notifications import NotificationsService

        db_session.add(_make_patient("PT_NS001"))
        await db_session.flush()

        llm = FakeLLMProvider()
        service = NotificationsService(session=db_session, llm=llm)

        response = await service.generate_smart(
            patient_id="PT_NS001",
            trigger_kind="streak_at_risk",
            context={"streak_days": 5, "activity": "yoga"},
        )

        # Response carries required fields
        assert response.title
        assert response.body
        assert response.cta
        assert response.disclaimer
        assert response.ai_meta is not None

        # Row was persisted — list should return at least one notification
        from app.repositories.notification_repo import NotificationRepository

        repo = NotificationRepository(db_session)
        rows = await repo.list(patient_id="PT_NS001")
        assert len(rows) == 1
        assert rows[0].patient_id == "PT_NS001"
        assert rows[0].kind == "streak_at_risk"
        assert rows[0].title == response.title
        assert rows[0].body == response.body

    async def test_generate_smart_isolation(
        self, db_session: AsyncSession
    ) -> None:
        """Notifications created for patient A are invisible to patient B."""
        from app.ai.llm import FakeLLMProvider
        from app.repositories.notification_repo import NotificationRepository
        from app.services.notifications import NotificationsService

        db_session.add(_make_patient("PT_NS_A"))
        db_session.add(_make_patient("PT_NS_B"))
        await db_session.flush()

        llm = FakeLLMProvider()
        service = NotificationsService(session=db_session, llm=llm)

        # Create notification for patient A only
        await service.generate_smart(
            patient_id="PT_NS_A",
            trigger_kind="protocol_due",
            context={},
        )

        repo = NotificationRepository(db_session)
        # Patient A sees their notification
        rows_a = await repo.list(patient_id="PT_NS_A")
        assert len(rows_a) == 1

        # Patient B sees nothing
        rows_b = await repo.list(patient_id="PT_NS_B")
        assert len(rows_b) == 0


# ---------------------------------------------------------------------------
# TestClinicalReviewService
# ---------------------------------------------------------------------------


class TestClinicalReviewService:
    """Round-trip + isolation tests for ClinicalReviewService."""

    async def test_create_returns_persisted_review(
        self, db_session: AsyncSession
    ) -> None:
        """create() persists a ClinicalReview and returns the row."""
        from app.services.clinical_review import ClinicalReviewService

        db_session.add(_make_patient("PT_CR001"))
        await db_session.flush()

        service = ClinicalReviewService(session=db_session)
        review = await service.create(
            patient_id="PT_CR001",
            reason="Elevated cardiovascular markers detected in wellness check",
            ai_flag={"signal": "elevated_apob", "severity": "moderate"},
        )

        assert review.id is not None
        assert review.patient_id == "PT_CR001"
        assert review.reason == "Elevated cardiovascular markers detected in wellness check"
        assert review.status == "pending"
        assert review.ai_flag == {"signal": "elevated_apob", "severity": "moderate"}

    async def test_create_isolation(self, db_session: AsyncSession) -> None:
        """Reviews created for patient A are invisible to patient B."""
        from app.repositories.clinical_review_repo import ClinicalReviewRepository
        from app.services.clinical_review import ClinicalReviewService

        db_session.add(_make_patient("PT_CR_A"))
        db_session.add(_make_patient("PT_CR_B"))
        await db_session.flush()

        service = ClinicalReviewService(session=db_session)
        await service.create(
            patient_id="PT_CR_A",
            reason="Some clinical signal",
            ai_flag=None,
        )

        repo = ClinicalReviewRepository(db_session)
        rows_a = await repo.list(patient_id="PT_CR_A")
        assert len(rows_a) == 1

        rows_b = await repo.list(patient_id="PT_CR_B")
        assert len(rows_b) == 0


# ---------------------------------------------------------------------------
# TestReferralService
# ---------------------------------------------------------------------------


class TestReferralService:
    """Round-trip + isolation tests for ReferralService."""

    async def test_create_returns_persisted_referral(
        self, db_session: AsyncSession
    ) -> None:
        """create() persists a Referral with the given code and returns the row."""
        from app.services.referral import ReferralService

        db_session.add(_make_patient("PT_RF001"))
        await db_session.flush()

        service = ReferralService(session=db_session)
        referral = await service.create(
            patient_id="PT_RF001",
            code="REF-ABCD-1234",
        )

        assert referral.id is not None
        assert referral.patient_id == "PT_RF001"
        assert referral.code == "REF-ABCD-1234"
        assert referral.status == "pending"
        assert referral.referred_patient_id is None

    async def test_create_isolation(self, db_session: AsyncSession) -> None:
        """Referrals created for patient A are invisible to patient B."""
        from app.repositories.referral_repo import ReferralRepository
        from app.services.referral import ReferralService

        db_session.add(_make_patient("PT_RF_A"))
        db_session.add(_make_patient("PT_RF_B"))
        await db_session.flush()

        service = ReferralService(session=db_session)
        await service.create(
            patient_id="PT_RF_A",
            code="REF-AAAA-0001",
        )

        repo = ReferralRepository(db_session)
        rows_a = await repo.list(patient_id="PT_RF_A")
        assert len(rows_a) == 1

        rows_b = await repo.list(patient_id="PT_RF_B")
        assert len(rows_b) == 0


# ---------------------------------------------------------------------------
# TestMessagesService
# ---------------------------------------------------------------------------


class TestMessagesService:
    """Round-trip + isolation tests for MessagesService."""

    async def test_post_and_list_messages(self, db_session: AsyncSession) -> None:
        """post() persists a Message; list() retrieves it for the same patient."""
        from app.services.messages import MessagesService

        db_session.add(_make_patient("PT_MSG001"))
        await db_session.flush()

        service = MessagesService(session=db_session)

        msg1 = await service.post(
            patient_id="PT_MSG001",
            content="Hello from the patient",
            sender="patient",
        )
        msg2 = await service.post(
            patient_id="PT_MSG001",
            content="Reply from the clinician",
            sender="clinician",
        )

        assert msg1.id is not None
        assert msg1.patient_id == "PT_MSG001"
        assert msg1.content == "Hello from the patient"
        assert msg1.sender == "patient"

        messages = await service.list(patient_id="PT_MSG001")
        assert len(messages) == 2
        # list() returns ASC order (chronological)
        assert messages[0].content == "Hello from the patient"
        assert messages[1].content == "Reply from the clinician"

    async def test_list_isolation(self, db_session: AsyncSession) -> None:
        """Messages posted for patient A are invisible to patient B."""
        from app.services.messages import MessagesService

        db_session.add(_make_patient("PT_MSG_A"))
        db_session.add(_make_patient("PT_MSG_B"))
        await db_session.flush()

        service = MessagesService(session=db_session)
        await service.post(
            patient_id="PT_MSG_A",
            content="Message for patient A",
            sender="clinician",
        )

        # Patient A sees their message
        msgs_a = await service.list(patient_id="PT_MSG_A")
        assert len(msgs_a) == 1

        # Patient B sees nothing
        msgs_b = await service.list(patient_id="PT_MSG_B")
        assert len(msgs_b) == 0
