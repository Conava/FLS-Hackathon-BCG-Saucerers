"""Records Q&A router.

Provides a single endpoint that accepts a natural-language question about a
patient's EHR records and returns a RAG-generated answer with citations.

Endpoint:
    POST /patients/{patient_id}/records/qa

Authentication:
    Every request must carry a valid ``X-API-Key`` header (enforced by
    ``api_key_auth``).

Isolation guarantee:
    The ``patient_id`` path parameter flows directly into ``RAGService.ask``
    as the hard-scoped ``patient_id`` filter.  Cross-patient access is
    prevented at the SQL level — no request can retrieve another patient's
    records.

PHI policy:
    No patient-identifiable information is written to logs.  Only
    ``request_id``, ``model``, ``prompt_name``, ``token_in``, ``token_out``,
    and ``latency_ms`` are emitted by ``RAGService``.

Dependency injection:
    ``get_rag_service`` is a FastAPI dependency factory.  Tests override it
    to inject a ``FakeLLMProvider``-backed ``RAGService`` so no real Gemini
    calls are made during the test suite.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.llm import FakeLLMProvider, LLMProvider, get_llm_provider
from app.core.config import Settings
from app.core.security import api_key_auth
from app.db.session import get_session
from app.repositories.patient_repo import PatientRepository
from app.schemas.records_qa import RecordsQARequest, RecordsQAResponse
from app.services.rag import RAGService

router = APIRouter(prefix="/patients", tags=["records-qa"])

# Type alias for the session dependency to keep signatures concise.
_Session = Annotated[AsyncSession, Depends(get_session)]
_Auth = Annotated[None, Depends(api_key_auth)]


# ---------------------------------------------------------------------------
# RAGService dependency factory
# ---------------------------------------------------------------------------


def get_rag_service(session: _Session) -> RAGService:
    """FastAPI dependency that creates a ``RAGService`` backed by the configured LLM provider.

    Reads ``llm_provider`` from ``Settings`` to decide which ``LLMProvider``
    implementation to use.  In tests this dependency is overridden to inject a
    ``FakeLLMProvider``-backed ``RAGService`` — no real Gemini calls are made.

    Args:
        session: The injected ``AsyncSession`` for this request.

    Returns:
        A ``RAGService`` ready to answer questions scoped to a patient.
    """
    settings = Settings()
    llm: LLMProvider = get_llm_provider(settings)
    return RAGService(session=session, llm=llm)


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.post(
    "/{patient_id}/records/qa",
    response_model=RecordsQAResponse,
    tags=["records-qa"],
    summary="Answer a question about a patient's EHR records using RAG",
)
async def post_records_qa(
    patient_id: str,
    body: RecordsQARequest,
    session: _Session,
    _auth: _Auth,
    rag_service: Annotated[RAGService, Depends(get_rag_service)],
) -> RecordsQAResponse:
    """Accept a natural-language question and return a RAG-generated answer.

    The endpoint:
    1. Validates that the patient exists — returns 404 if not.
    2. Delegates to ``RAGService.ask`` which embeds the question, retrieves the
       top-k most relevant EHR records via pgvector cosine search (hard-scoped
       to ``patient_id``), calls the LLM with a ``records-qa`` system prompt,
       and returns a ``RecordsQAResponse`` with answer, citations, disclaimer,
       and ``AIMeta``.

    Isolation guarantee:
        The ``patient_id`` path parameter is the sole scope key.  No data from
        other patients can appear in the response.

    Args:
        patient_id: Path parameter — the patient to query, e.g. ``PT0282``.
        body:        Request body containing the natural-language ``question``.
        session:     Injected ``AsyncSession`` (per-request).
        _auth:       ``api_key_auth`` result (validates ``X-API-Key`` header).
        rag_service: Injected ``RAGService`` (overridable for tests).

    Returns:
        ``RecordsQAResponse`` with answer, citations, disclaimer, and ai_meta.

    Raises:
        HTTPException 404: If ``patient_id`` does not exist in the database.
    """
    # Guard: patient must exist before we issue any RAG query.
    patient_repo = PatientRepository(session)
    patient = await patient_repo.get(patient_id=patient_id)
    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient {patient_id!r} not found.",
        )

    return await rag_service.ask(patient_id=patient_id, question=body.question)
