"""Integration tests for the POST /v1/patients/{pid}/records/qa endpoint.

Uses a local mini-app-factory fixture (``records_qa_client``) so this test
module is independent of T23b (main.py router registration).  The fixture
mounts only the records_qa router (and health for the probe) under ``/v1``,
and overrides both ``get_session`` and the RAGService dependency with test
doubles.

Two test patients are seeded:
  - RQPT_A ("Alice QA"): two EHR records about cholesterol.
  - RQPT_B ("Bob QA"): two EHR records about diabetes.

Tests:
  1. test_post_records_qa_happy_path
       — POST a valid question for patient A; assert 200, answer present,
         disclaimer present, ai_meta present, citations are a list.
  2. test_post_records_qa_requires_api_key
       — Without X-API-Key the endpoint returns 401.
  3. test_post_records_qa_unknown_patient_returns_404
       — Patient that does not exist returns 404.
  4. test_post_records_qa_cross_patient_isolation
       — Seed two patients; POST a question as patient A; assert no citation
         record IDs from patient B appear in the response.

Stack: pytest-asyncio session-scoped loop, Testcontainers Postgres + pgvector.
"""

from __future__ import annotations

import datetime
import json
from typing import Any

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

import app.models  # noqa: F401 — registers tables with SQLModel metadata
from app.models import EHRRecord, Patient

HEADERS = {"X-API-Key": "test-key"}

# ---------------------------------------------------------------------------
# Seed helpers
# ---------------------------------------------------------------------------

_DT = datetime.datetime(2026, 1, 1, 0, 0, 0)  # naive UTC sentinel


def _make_patient(patient_id: str, name: str) -> Patient:
    return Patient(
        patient_id=patient_id,
        name=name,
        age=45,
        sex="unknown",
        country="DE",
    )


def _make_ehr(patient_id: str, payload: dict[str, Any]) -> EHRRecord:
    return EHRRecord(
        patient_id=patient_id,
        record_type="condition",
        recorded_at=_DT,
        payload=payload,
        source="test",
    )


async def _seed_two_patients(session: AsyncSession) -> tuple[list[int], list[int]]:
    """Seed RQPT_A (cholesterol) and RQPT_B (diabetes) with EHR records and embeddings.

    Returns (patient_a_record_ids, patient_b_record_ids).
    """
    from app.ai.llm import FakeLLMProvider

    pa = _make_patient("RQPT_A", "Alice QA")
    pb = _make_patient("RQPT_B", "Bob QA")
    session.add(pa)
    session.add(pb)
    await session.flush()

    records_a = [
        _make_ehr("RQPT_A", {"icd_code": "E78.5", "description": "Hyperlipidemia elevated LDL"}),
        _make_ehr("RQPT_A", {"name": "Atorvastatin", "dose": "20mg"}),
    ]
    records_b = [
        _make_ehr("RQPT_B", {"icd_code": "E11", "description": "Type 2 diabetes HbA1c"}),
        _make_ehr("RQPT_B", {"name": "Metformin", "dose": "500mg"}),
    ]

    for r in records_a + records_b:
        session.add(r)
    await session.flush()

    # Populate embeddings so the vector search actually works.
    llm = FakeLLMProvider()
    all_records = records_a + records_b
    texts = [
        f"{r.record_type}: {json.dumps(r.payload, ensure_ascii=False)}"
        for r in all_records
    ]
    vectors = await llm.embed(texts)
    for record, vec in zip(all_records, vectors):
        record.embedding = vec

    await session.flush()
    await session.commit()

    return (
        [r.id for r in records_a if r.id is not None],
        [r.id for r in records_b if r.id is not None],
    )


async def _seed_patient_a_only(session: AsyncSession) -> list[int]:
    """Seed RQPT_A only. Returns patient A's record IDs."""
    a_ids, _ = await _seed_two_patients(session)
    return a_ids


# ---------------------------------------------------------------------------
# Mini app factory fixture
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(loop_scope="session")
async def records_qa_client(db_session: AsyncSession) -> AsyncClient:  # type: ignore[return]
    """Build a minimal FastAPI app with only the records_qa router and return a test client.

    Overrides ``get_session`` to use the testcontainers-backed ``db_session``.
    Overrides the RAGService factory dependency to inject a FakeLLMProvider-backed
    RAGService so no real Gemini calls are made.
    """
    from fastapi import FastAPI
    from httpx import AsyncClient
    from httpx._transports.asgi import ASGITransport

    from app.db.session import get_session
    from app.routers import health
    from app.routers.records_qa import get_rag_service, router as rqa_router

    app = FastAPI()
    app.include_router(health.router)
    app.include_router(rqa_router, prefix="/v1")

    async def _override_session():  # type: ignore[return]
        yield db_session

    from app.ai.llm import FakeLLMProvider
    from app.services.rag import RAGService

    def _override_rag_service() -> RAGService:
        # db_session is captured from the outer fixture scope — no sub-dep resolution needed
        return RAGService(db_session, FakeLLMProvider())

    app.dependency_overrides[get_session] = _override_session
    app.dependency_overrides[get_rag_service] = _override_rag_service

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_post_records_qa_happy_path(
    records_qa_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """POST a valid question; assert 200 with answer, disclaimer, ai_meta, citations."""
    await _seed_patient_a_only(db_session)

    resp = await records_qa_client.post(
        "/v1/patients/RQPT_A/records/qa",
        headers=HEADERS,
        json={"question": "What cholesterol medications am I taking?"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert "answer" in data and data["answer"], "answer must be non-empty"
    assert "disclaimer" in data and data["disclaimer"], "disclaimer must be present"
    assert "ai_meta" in data, "ai_meta must be present"
    ai_meta = data["ai_meta"]
    assert ai_meta.get("prompt_name") == "records-qa", (
        f"Expected prompt_name='records-qa', got {ai_meta.get('prompt_name')!r}"
    )
    assert isinstance(data.get("citations"), list), "citations must be a list"


async def test_post_records_qa_requires_api_key(
    records_qa_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Requests without X-API-Key must be rejected with 401."""
    await _seed_patient_a_only(db_session)

    resp = await records_qa_client.post(
        "/v1/patients/RQPT_A/records/qa",
        json={"question": "What are my conditions?"},
    )
    assert resp.status_code == 401, f"Expected 401, got {resp.status_code}: {resp.text}"


async def test_post_records_qa_unknown_patient_returns_404(
    records_qa_client: AsyncClient,
) -> None:
    """Requesting Q&A for a non-existent patient must return 404."""
    resp = await records_qa_client.post(
        "/v1/patients/UNKNOWN_PATIENT_XYZ/records/qa",
        headers=HEADERS,
        json={"question": "What are my records?"},
    )
    assert resp.status_code == 404, f"Expected 404, got {resp.status_code}: {resp.text}"


async def test_post_records_qa_cross_patient_isolation(
    records_qa_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Citation record IDs must not include any record owned by the other patient.

    Seeds two patients (RQPT_A and RQPT_B).  POSTs a question as RQPT_A.
    Asserts that every citation.record_id in the response belongs to RQPT_A's
    record set — none from RQPT_B.
    """
    a_ids, b_ids = await _seed_two_patients(db_session)

    resp = await records_qa_client.post(
        "/v1/patients/RQPT_A/records/qa",
        headers=HEADERS,
        json={"question": "What is my cholesterol status?"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()

    cited_ids = {c["record_id"] for c in data.get("citations", [])}
    for bid in b_ids:
        assert bid not in cited_ids, (
            f"ISOLATION BREACH: patient B record {bid} appeared in patient A's citations. "
            f"Patient A record IDs: {a_ids}, cited: {cited_ids}"
        )
