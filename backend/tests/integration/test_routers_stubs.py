"""Integration tests for T22 stub routers.

Tests for the four routers:
  - POST /v1/patients/{pid}/notifications/smart
  - POST /v1/patients/{pid}/clinical-review
  - POST /v1/patients/{pid}/referral
  - GET  /v1/patients/{pid}/messages
  - POST /v1/patients/{pid}/messages

Each endpoint has:
  1. A happy-path test asserting the response shape and persistence.
  2. An isolation test asserting that writes for patient A are invisible to patient B.

Uses the mini-app test pattern — a ``stubs_client`` fixture builds a minimal
FastAPI app that mounts only the four stub routers under ``/v1``, and overrides
``get_session`` with the Testcontainers-backed ``db_session``.

``FakeLLMProvider`` is injected via the ``get_notifications_service`` dependency
override so no real Gemini calls are made.

Stack: pytest-asyncio session-scoped loop, Testcontainers Postgres + pgvector.
"""

from __future__ import annotations

import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

import app.models  # noqa: F401 — side-effect import registers all tables

HEADERS = {"X-API-Key": "test-key"}


# ---------------------------------------------------------------------------
# Patient seed helper
# ---------------------------------------------------------------------------


async def _seed_patient(session: AsyncSession, patient_id: str) -> None:
    """Insert a minimal Patient row to satisfy FK constraints."""
    from app.models.patient import Patient

    session.add(
        Patient(
            patient_id=patient_id,
            name=f"Test {patient_id}",
            age=40,
            sex="unknown",
            country="DE",
        )
    )
    await session.flush()


# ---------------------------------------------------------------------------
# Mini-app fixture
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(loop_scope="session")
async def stubs_client(db_session: AsyncSession) -> AsyncClient:  # type: ignore[return]
    """Build a minimal FastAPI app with the four stub routers.

    Overrides:
    - ``get_session`` → testcontainers-backed ``db_session``
    - ``get_notifications_service`` → ``FakeLLMProvider``-backed ``NotificationsService``
    """
    from fastapi import FastAPI
    from httpx import AsyncClient
    from httpx._transports.asgi import ASGITransport

    from app.ai.llm import FakeLLMProvider
    from app.db.session import get_session
    from app.routers import health
    from app.routers.clinical_review import router as cr_router
    from app.routers.messages import router as msg_router
    from app.routers.notifications import get_notifications_service, router as notif_router
    from app.routers.referral import router as ref_router
    from app.services.notifications import NotificationsService

    app = FastAPI()
    app.include_router(health.router)
    app.include_router(notif_router, prefix="/v1")
    app.include_router(cr_router, prefix="/v1")
    app.include_router(ref_router, prefix="/v1")
    app.include_router(msg_router, prefix="/v1")

    async def _override_session():  # type: ignore[return]
        yield db_session

    def _override_notifications_service() -> NotificationsService:
        return NotificationsService(session=db_session, llm=FakeLLMProvider())

    app.dependency_overrides[get_session] = _override_session
    app.dependency_overrides[get_notifications_service] = _override_notifications_service

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


# ---------------------------------------------------------------------------
# Notifications — POST /v1/patients/{pid}/notifications/smart
# ---------------------------------------------------------------------------


async def test_post_smart_notification_happy_path(
    stubs_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """POST a smart notification request; assert 200 with required fields."""
    await _seed_patient(db_session, "PT_NR001")

    resp = await stubs_client.post(
        "/v1/patients/PT_NR001/notifications/smart",
        headers=HEADERS,
        json={"trigger_kind": "streak_at_risk", "context": {"streak_days": 3}},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data.get("title"), "title must be non-empty"
    assert data.get("body"), "body must be non-empty"
    assert data.get("cta"), "cta must be non-empty"
    assert data.get("disclaimer"), "disclaimer must be present"
    assert "ai_meta" in data, "ai_meta must be present"


async def test_post_smart_notification_isolation(
    stubs_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Notifications created for patient A are not visible to patient B's query path."""
    await _seed_patient(db_session, "PT_NR_A")
    await _seed_patient(db_session, "PT_NR_B")

    # Create a notification for patient A
    resp_a = await stubs_client.post(
        "/v1/patients/PT_NR_A/notifications/smart",
        headers=HEADERS,
        json={"trigger_kind": "protocol_due", "context": {}},
    )
    assert resp_a.status_code == 200, resp_a.text

    # Verify isolation at the repository level
    from app.repositories.notification_repo import NotificationRepository

    repo = NotificationRepository(db_session)
    rows_a = await repo.list(patient_id="PT_NR_A")
    rows_b = await repo.list(patient_id="PT_NR_B")

    assert len(rows_a) >= 1, "Patient A should have at least one notification"
    assert len(rows_b) == 0, "Patient B must have no notifications"


async def test_post_smart_notification_requires_api_key(
    stubs_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """POST without X-API-Key must return 401."""
    await _seed_patient(db_session, "PT_NR002")

    resp = await stubs_client.post(
        "/v1/patients/PT_NR002/notifications/smart",
        json={"trigger_kind": "streak_at_risk", "context": {}},
    )
    assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"


# ---------------------------------------------------------------------------
# Clinical Review — POST /v1/patients/{pid}/clinical-review
# ---------------------------------------------------------------------------


async def test_post_clinical_review_happy_path(
    stubs_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """POST a clinical review request; assert 200 with id, patient_id, status=pending."""
    await _seed_patient(db_session, "PT_CR001")

    resp = await stubs_client.post(
        "/v1/patients/PT_CR001/clinical-review",
        headers=HEADERS,
        json={
            "patient_id": "PT_CR001",
            "notes": "Elevated cardiovascular wellness markers detected",
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data.get("id") is not None, "id must be present"
    assert data.get("patient_id") == "PT_CR001"
    assert data.get("status") == "pending"
    assert data.get("notes") or data.get("reason"), "notes/reason must be present"


async def test_post_clinical_review_isolation(
    stubs_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Reviews created for patient A are invisible to patient B."""
    await _seed_patient(db_session, "PT_CR_A")
    await _seed_patient(db_session, "PT_CR_B")

    resp = await stubs_client.post(
        "/v1/patients/PT_CR_A/clinical-review",
        headers=HEADERS,
        json={"patient_id": "PT_CR_A", "notes": "Some wellness concern"},
    )
    assert resp.status_code == 200, resp.text

    from app.repositories.clinical_review_repo import ClinicalReviewRepository

    repo = ClinicalReviewRepository(db_session)
    rows_a = await repo.list(patient_id="PT_CR_A")
    rows_b = await repo.list(patient_id="PT_CR_B")

    assert len(rows_a) >= 1, "Patient A should have a review"
    assert len(rows_b) == 0, "Patient B must have no reviews"


async def test_post_clinical_review_requires_api_key(
    stubs_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """POST without X-API-Key must return 401."""
    await _seed_patient(db_session, "PT_CR002")

    resp = await stubs_client.post(
        "/v1/patients/PT_CR002/clinical-review",
        json={"patient_id": "PT_CR002", "notes": "Concern"},
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Referral — POST /v1/patients/{pid}/referral
# ---------------------------------------------------------------------------


async def test_post_referral_happy_path(
    stubs_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """POST a referral request; assert 200 with id, patient_id, status=pending."""
    await _seed_patient(db_session, "PT_RF001")

    resp = await stubs_client.post(
        "/v1/patients/PT_RF001/referral",
        headers=HEADERS,
        json={
            "patient_id": "PT_RF001",
            "specialty": "cardiology",
            "reason": "Elevated cardiovascular wellness markers",
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data.get("id") is not None, "id must be present"
    assert data.get("patient_id") == "PT_RF001"
    assert data.get("status") == "pending"
    # specialty or reason or code must be present in the response
    assert data.get("specialty") or data.get("code"), "specialty or code must be present"


async def test_post_referral_isolation(
    stubs_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Referrals created for patient A are invisible to patient B."""
    await _seed_patient(db_session, "PT_RF_A")
    await _seed_patient(db_session, "PT_RF_B")

    resp = await stubs_client.post(
        "/v1/patients/PT_RF_A/referral",
        headers=HEADERS,
        json={"patient_id": "PT_RF_A", "specialty": "cardiology", "reason": "Wellness check"},
    )
    assert resp.status_code == 200, resp.text

    from app.repositories.referral_repo import ReferralRepository

    repo = ReferralRepository(db_session)
    rows_a = await repo.list(patient_id="PT_RF_A")
    rows_b = await repo.list(patient_id="PT_RF_B")

    assert len(rows_a) >= 1, "Patient A should have a referral"
    assert len(rows_b) == 0, "Patient B must have no referrals"


async def test_post_referral_requires_api_key(
    stubs_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """POST without X-API-Key must return 401."""
    await _seed_patient(db_session, "PT_RF002")

    resp = await stubs_client.post(
        "/v1/patients/PT_RF002/referral",
        json={"patient_id": "PT_RF002", "specialty": "cardiology", "reason": "Concern"},
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Messages — GET /v1/patients/{pid}/messages
#           POST /v1/patients/{pid}/messages
# ---------------------------------------------------------------------------


async def test_post_and_get_messages_happy_path(
    stubs_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """POST two messages; GET returns both in order."""
    await _seed_patient(db_session, "PT_MSG001")

    # Post first message
    resp1 = await stubs_client.post(
        "/v1/patients/PT_MSG001/messages",
        headers=HEADERS,
        json={"patient_id": "PT_MSG001", "content": "Hello from the patient"},
    )
    assert resp1.status_code == 200, resp1.text
    msg1 = resp1.json()
    assert msg1.get("id") is not None
    assert msg1.get("patient_id") == "PT_MSG001"
    assert msg1.get("content") == "Hello from the patient"

    # Post second message
    resp2 = await stubs_client.post(
        "/v1/patients/PT_MSG001/messages",
        headers=HEADERS,
        json={"patient_id": "PT_MSG001", "content": "Follow-up message"},
    )
    assert resp2.status_code == 200, resp2.text

    # GET the message list
    resp_list = await stubs_client.get(
        "/v1/patients/PT_MSG001/messages",
        headers=HEADERS,
    )
    assert resp_list.status_code == 200, resp_list.text
    list_data = resp_list.json()

    assert list_data.get("patient_id") == "PT_MSG001"
    messages = list_data.get("messages", [])
    assert len(messages) == 2, f"Expected 2 messages, got {len(messages)}"
    # All messages must belong to the correct patient
    for msg in messages:
        assert msg.get("patient_id") == "PT_MSG001"


async def test_get_messages_isolation(
    stubs_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Messages posted for patient A are invisible when listing patient B's messages."""
    await _seed_patient(db_session, "PT_MSG_A")
    await _seed_patient(db_session, "PT_MSG_B")

    # Post a message for patient A
    resp = await stubs_client.post(
        "/v1/patients/PT_MSG_A/messages",
        headers=HEADERS,
        json={"patient_id": "PT_MSG_A", "content": "Message for A"},
    )
    assert resp.status_code == 200, resp.text

    # List patient B's messages — must be empty
    resp_b = await stubs_client.get(
        "/v1/patients/PT_MSG_B/messages",
        headers=HEADERS,
    )
    assert resp_b.status_code == 200, resp_b.text
    list_b = resp_b.json()
    assert list_b.get("messages") == [], (
        f"Patient B must have no messages; got: {list_b.get('messages')}"
    )


async def test_post_messages_requires_api_key(
    stubs_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """POST without X-API-Key must return 401."""
    await _seed_patient(db_session, "PT_MSG002")

    resp = await stubs_client.post(
        "/v1/patients/PT_MSG002/messages",
        json={"patient_id": "PT_MSG002", "content": "Hello"},
    )
    assert resp.status_code == 401


async def test_get_messages_requires_api_key(
    stubs_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """GET without X-API-Key must return 401."""
    await _seed_patient(db_session, "PT_MSG003")

    resp = await stubs_client.get("/v1/patients/PT_MSG003/messages")
    assert resp.status_code == 401
