"""Integration tests for RAGService (T9).

Tests:
  1. test_ask_citations_scoped_to_patient_a
       — Two patients seeded with distinguishable EHR content.
         Ask as patient A; assert all citation record_ids belong to A.
  2. test_ask_disclaimer_present
       — Disclaimer is present in the response.
  3. test_ask_uses_records_qa_prompt
       — ai_meta.prompt_name is "records-qa".
  4. test_ask_returns_answer
       — The response must contain a non-empty answer string.
  5. test_ask_model_name_in_ai_meta
       — ai_meta.model must be 'gemini-2.5-pro'.
  6. test_regex_citation_path_exact_match
       — FakeLLMProvider subclass returns text with [ref:ehr_record.<id>] tags.
         Assert: citations contains EXACTLY those record_ids, dedup works, no
         fallback "all retrieved records" set is used.
  7. test_no_patient_b_ids_in_answer_text
       — No patient B record IDs appear in response.answer text (not just citations).

Isolation strategy: We insert records directly via ``db_session``.
``FakeLLMProvider.embed`` returns deterministic 768-d vectors keyed by text hash.
The cholesterol / diabetes distinction is enough signal because each text maps
to a unique deterministic vector.

Stack: pytest-asyncio session-scoped loop, Testcontainers Postgres + pgvector.
"""

from __future__ import annotations

import datetime
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

import app.models  # noqa: F401 — registers tables with SQLModel metadata
from app.ai.llm import FakeLLMProvider
from app.models import EHRRecord, Patient
from app.services.rag import RAGService

# ---------------------------------------------------------------------------
# Helpers
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


def _make_ehr(patient_id: str, content_desc: str, payload: dict[str, Any]) -> EHRRecord:
    """Create an EHRRecord with a condition payload.

    ``content_desc`` is embedded via FakeLLMProvider so its hash determines
    the vector.  The payload description is stored in the JSONB column.
    """
    return EHRRecord(
        patient_id=patient_id,
        record_type="condition",
        recorded_at=_DT,
        payload=payload,
        source="test",
        # embedding populated below via FakeLLMProvider
    )


async def _seed(session: AsyncSession) -> tuple[list[int], list[int]]:
    """Seed two patients with distinguishable EHR records.

    Patient A ("RAGPT_A") has records about high cholesterol.
    Patient B ("RAGPT_B") has records about diabetes.

    Returns two lists: (patient_a_record_ids, patient_b_record_ids).
    """
    # Patients
    pa = _make_patient("RAGPT_A", "Alice Test")
    pb = _make_patient("RAGPT_B", "Bob Test")
    session.add(pa)
    session.add(pb)
    await session.flush()

    # Patient A — cholesterol records
    records_a: list[EHRRecord] = [
        _make_ehr(
            "RAGPT_A",
            "high cholesterol elevated LDL lipid panel",
            {"icd_code": "E78.5", "description": "Hyperlipidemia with elevated LDL cholesterol"},
        ),
        _make_ehr(
            "RAGPT_A",
            "cholesterol medication statin therapy",
            {"name": "Atorvastatin", "dose": "20mg"},
        ),
    ]

    # Patient B — diabetes records
    records_b: list[EHRRecord] = [
        _make_ehr(
            "RAGPT_B",
            "diabetes type 2 elevated HbA1c blood glucose",
            {"icd_code": "E11", "description": "Type 2 diabetes mellitus with hyperglycemia"},
        ),
        _make_ehr(
            "RAGPT_B",
            "diabetes medication insulin metformin",
            {"name": "Metformin", "dose": "500mg"},
        ),
    ]

    for r in records_a + records_b:
        session.add(r)
    await session.flush()

    # Embed all records with FakeLLMProvider so vector search works.
    # FakeLLMProvider.embed derives vectors deterministically from text hash —
    # any stable content text produces a stable, distinct 768-d vector.
    llm = FakeLLMProvider()
    all_records = records_a + records_b

    # Build text representation consistent with _record_to_text in unified_profile
    import json

    texts = [
        f"{r.record_type}: {json.dumps(r.payload, ensure_ascii=False)}"
        for r in all_records
    ]
    vectors = await llm.embed(texts)
    for record, vec in zip(all_records, vectors):
        record.embedding = vec

    await session.flush()
    await session.commit()

    return [r.id for r in records_a if r.id is not None], [
        r.id for r in records_b if r.id is not None
    ]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_ask_citations_scoped_to_patient_a(db_session: AsyncSession) -> None:
    """All citations must reference records owned by patient A only.

    We ask a cholesterol-related question as patient A.  The RAG service must
    retrieve only patient A's records and include their IDs in citations.
    No patient B record ID may appear in the citation list.
    """
    a_ids, b_ids = await _seed(db_session)

    llm = FakeLLMProvider()
    svc = RAGService(db_session, llm)
    response = await svc.ask(patient_id="RAGPT_A", question="What is my cholesterol status?")

    # Every cited record must belong to patient A.
    cited_ids = {c.record_id for c in response.citations}
    for cid in cited_ids:
        assert cid in a_ids, (
            f"ISOLATION BREACH: citation references record {cid} "
            f"which is not in patient A's records {a_ids}"
        )

    # No patient B records must be cited.
    for bid in b_ids:
        assert bid not in cited_ids, (
            f"ISOLATION BREACH: patient B record {bid} appeared in patient A's response"
        )


@pytest.mark.integration
async def test_ask_disclaimer_present(db_session: AsyncSession) -> None:
    """The response must carry the mandatory wellness disclaimer."""
    await _seed(db_session)

    llm = FakeLLMProvider()
    svc = RAGService(db_session, llm)
    response = await svc.ask(patient_id="RAGPT_A", question="What medications am I taking?")

    assert response.disclaimer, "disclaimer must be non-empty"
    # The disclaimer must be wellness-framed (not medical advice language).
    assert "medical advice" in response.disclaimer.lower() or "wellness" in response.disclaimer.lower(), (
        f"Disclaimer does not appear to be wellness-framed: {response.disclaimer!r}"
    )


@pytest.mark.integration
async def test_ask_uses_records_qa_prompt(db_session: AsyncSession) -> None:
    """ai_meta.prompt_name must be 'records-qa'."""
    await _seed(db_session)

    llm = FakeLLMProvider()
    svc = RAGService(db_session, llm)
    response = await svc.ask(patient_id="RAGPT_A", question="Show me my recent lab results.")

    assert response.ai_meta.prompt_name == "records-qa", (
        f"Expected prompt_name='records-qa', got {response.ai_meta.prompt_name!r}"
    )


@pytest.mark.integration
async def test_ask_returns_answer(db_session: AsyncSession) -> None:
    """The response must contain a non-empty answer string."""
    await _seed(db_session)

    llm = FakeLLMProvider()
    svc = RAGService(db_session, llm)
    response = await svc.ask(patient_id="RAGPT_A", question="What conditions do I have?")

    assert response.answer, "answer must be non-empty"


@pytest.mark.integration
async def test_ask_model_name_in_ai_meta(db_session: AsyncSession) -> None:
    """ai_meta.model must be 'gemini-2.5-pro' as specified in the task."""
    await _seed(db_session)

    llm = FakeLLMProvider()
    svc = RAGService(db_session, llm)
    response = await svc.ask(patient_id="RAGPT_A", question="Tell me about my records.")

    assert response.ai_meta.model == "gemini-2.5-pro", (
        f"Expected model='gemini-2.5-pro', got {response.ai_meta.model!r}"
    )


@pytest.mark.integration
async def test_regex_citation_path_exact_match(db_session: AsyncSession) -> None:
    """The regex citation parser must extract exact record IDs from [ref:ehr_record.<id>] tags.

    Uses a FakeLLMProvider subclass whose generate() returns a deterministic
    string that embeds real patient-A record IDs in the ``[ref:ehr_record.<id>]``
    format.  Verifies:

    - ``response.citations`` contains EXACTLY those IDs (no extra fallback IDs).
    - The first record ID cited twice deduplicates to a single Citation entry.
    - No patient B record IDs appear in citations.
    - The fallback "all retrieved records" path is NOT used (would add B-patient
      records if it were triggered).
    """
    a_ids, b_ids = await _seed(db_session)

    # We need at least one patient-A record ID to embed in the fake answer.
    assert len(a_ids) >= 1, "seed must produce at least one patient-A record"
    target_id = a_ids[0]

    class _CitingFakeLLM(FakeLLMProvider):
        """Override generate() to return an answer with a real ehr_record citation.

        The answer cites ``target_id`` twice (to test dedup) and never cites
        any patient-B IDs.
        """

        async def generate(
            self,
            *,
            system: str,
            user: str,
            model: str,
            response_schema: type[BaseModel] | None = None,
        ) -> str:
            # Cite the same ID twice to verify deduplication
            return (
                f"Your cholesterol was elevated [ref:ehr_record.{target_id}]. "
                f"A statin was prescribed [ref:ehr_record.{target_id}]. "
                "This is wellness guidance, not medical advice."
            )

    llm = _CitingFakeLLM()
    svc = RAGService(db_session, llm)
    response = await svc.ask(patient_id="RAGPT_A", question="What is my cholesterol status?")

    cited_ids = [c.record_id for c in response.citations]

    # target_id must appear exactly once (dedup)
    assert cited_ids.count(target_id) == 1, (
        f"Expected exactly one citation for record {target_id}, got {cited_ids}"
    )

    # No patient B IDs must appear in citations
    cited_set = set(cited_ids)
    for bid in b_ids:
        assert bid not in cited_set, (
            f"ISOLATION BREACH: patient B record {bid} appeared in citations via regex path"
        )

    # The citations should come from the regex path ONLY — meaning only target_id
    # is cited (not the whole fallback set of all retrieved records).
    # The fallback is triggered when citations is empty; since we have at least one
    # citation from the regex, the fallback must NOT have fired.
    assert len(cited_ids) == 1, (
        f"Expected exactly 1 citation (deduped target_id), got {cited_ids} — "
        "fallback 'all retrieved records' may have fired instead of regex path"
    )


@pytest.mark.integration
async def test_no_patient_b_ids_in_answer_text(db_session: AsyncSession) -> None:
    """No patient B record IDs may appear in the answer text itself.

    The docstring for test_ask_citations_scoped_to_patient_a already claims
    isolation at the citation level.  This test extends that guarantee to the
    raw answer string: even if an ID somehow leaked into the LLM response text,
    it must not be a B-patient record ID.
    """
    a_ids, b_ids = await _seed(db_session)

    llm = FakeLLMProvider()
    svc = RAGService(db_session, llm)
    response = await svc.ask(patient_id="RAGPT_A", question="What is my cholesterol status?")

    answer_text = response.answer
    for bid in b_ids:
        # The answer text must not reference any B-patient record by its numeric ID
        assert str(bid) not in answer_text, (
            f"ISOLATION BREACH: patient B record ID {bid} appeared in answer text: "
            f"{answer_text!r}"
        )
