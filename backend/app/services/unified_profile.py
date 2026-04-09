"""UnifiedProfileService — orchestrates DataSource adapters into the database.

Architecture
------------
The service consumes any registered ``DataSource`` (resolved by name from the
adapter registry) and writes Patient, LifestyleProfile, EHRRecord, and
WearableDay rows into the database using a streaming loop.

Idempotency strategy (documented trade-off for hackathon)
----------------------------------------------------------
* ``Patient`` and ``LifestyleProfile`` use ``session.merge()`` — ON CONFLICT
  on the primary key updates all columns.
* ``EHRRecord`` rows are **delete-then-insert** per patient: before inserting
  this patient's records we DELETE all existing EHRRecord rows for that
  patient_id. Same for WearableDay. This is simpler than natural-key upserts
  and fully correct at 1 k patients × tens of records.

Batching
--------
We commit every N=50 patients. Each commit flushes DB writes, releases row
locks, and bounds the session's in-memory state.

PHI policy
----------
No patient name, date of birth, or other PHI is logged. Only aggregate counts
and duration are emitted to the structured logger.
"""

from __future__ import annotations

import dataclasses
import json
import logging
import time
from typing import TYPE_CHECKING, Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters import get_source
from app.adapters.base import PatientData
from app.core.logging import get_logger
from app.models import EHRRecord, WearableDay

if TYPE_CHECKING:
    from app.ai.llm import LLMProvider

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Number of patients between commits — bounds memory and lock duration.
_BATCH_SIZE: int = 50

#: Number of EHR records to embed in a single LLM batch call.
_EMBED_BATCH_SIZE: int = 100

_logger: logging.Logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# IngestReport dataclass — returned by UnifiedProfileService.ingest()
# ---------------------------------------------------------------------------


@dataclasses.dataclass
class IngestReport:
    """Summary of a completed ingest run.

    Attributes
    ----------
    source:
        The adapter name used for this run (e.g. ``"csv"``).
    patients_ingested:
        Number of patients written to the database.
    ehr_records:
        Total EHR records inserted across all patients.
    wearable_days:
        Total wearable-day rows inserted across all patients.
    duration_seconds:
        Wall-clock time in seconds for the full ingest run.
    """

    source: str
    patients_ingested: int
    ehr_records: int
    wearable_days: int
    duration_seconds: float

    def __str__(self) -> str:
        return (
            f"IngestReport(source={self.source!r}, "
            f"patients={self.patients_ingested}, "
            f"ehr_records={self.ehr_records}, "
            f"wearable_days={self.wearable_days}, "
            f"duration={self.duration_seconds:.2f}s)"
        )


# ---------------------------------------------------------------------------
# UnifiedProfileService
# ---------------------------------------------------------------------------


class UnifiedProfileService:
    """Orchestrates a registered DataSource into the database.

    Parameters
    ----------
    session:
        An open ``AsyncSession``. The caller owns the session lifecycle;
        this service only adds objects and commits in batches.
    llm_provider:
        Optional LLM provider used to embed ``EHRRecord.content`` after
        each batch is written.  When ``None`` (default) embeddings are
        left as ``NULL`` — preserving backward-compatibility for callers
        that do not need RAG.

    Usage::

        svc = UnifiedProfileService(session)
        report = await svc.ingest("csv", data_dir=Path("./data"))
        print(report)
    """

    def __init__(
        self,
        session: AsyncSession,
        llm_provider: LLMProvider | None = None,
    ) -> None:
        self._session = session
        self._llm_provider = llm_provider

    async def ingest(self, source_name: str, **source_kwargs: Any) -> IngestReport:
        """Drain a registered DataSource into the database.

        Iterates all patients from the named adapter and writes them to the
        database in batches of :data:`_BATCH_SIZE`. The operation is idempotent:
        running it twice on the same data leaves the database in the same state.

        Parameters
        ----------
        source_name:
            Registry key of the adapter to use (e.g. ``"csv"``).
        **source_kwargs:
            Forwarded to the adapter constructor (e.g. ``data_dir=Path(...)``).

        Returns
        -------
        IngestReport
            Summary of the completed run.

        Raises
        ------
        KeyError
            If ``source_name`` is not registered.
        Exception
            Any DB or adapter error propagates; partial batches are NOT
            committed on failure — the caller must handle rollback.
        """
        source = get_source(source_name, **source_kwargs)
        session = self._session

        start = time.monotonic()
        patients_ingested = 0
        total_ehr = 0
        total_wearable = 0

        async for patient_data in source.iter_patients():  # type: ignore[attr-defined]
            await self._write_patient(patient_data)

            patients_ingested += 1
            total_ehr += len(patient_data.ehr_records)
            total_wearable += len(patient_data.wearable_days)

            # Progress log every 100 patients (no PHI — only counts)
            if patients_ingested % 100 == 0:
                _logger.info(
                    "ingest progress",
                    extra={
                        "source": source_name,
                        "patients_ingested": patients_ingested,
                        "ehr_records": total_ehr,
                        "wearable_days": total_wearable,
                    },
                )

            # Commit every N patients to bound memory and lock duration
            if patients_ingested % _BATCH_SIZE == 0:
                await session.commit()

        # Final commit for the last partial batch
        await session.commit()

        # After all patients are written, populate embeddings if an LLM provider
        # was supplied.  We do this in one pass over all records so the LLM
        # batching is maximally efficient (100 at a time).
        if self._llm_provider is not None:
            await self._embed_all_records()
            await session.commit()

        duration = time.monotonic() - start
        report = IngestReport(
            source=source_name,
            patients_ingested=patients_ingested,
            ehr_records=total_ehr,
            wearable_days=total_wearable,
            duration_seconds=duration,
        )
        _logger.info(
            "ingest complete",
            extra={
                "source": source_name,
                "patients_ingested": patients_ingested,
                "ehr_records": total_ehr,
                "wearable_days": total_wearable,
                "duration_seconds": round(duration, 2),
            },
        )
        return report

    async def _write_patient(self, patient_data: PatientData) -> None:
        """Write a single patient's full bundle to the database.

        Strategy:
        1. Upsert ``Patient`` via ``session.merge()`` (PK-based).
        2. Upsert ``LifestyleProfile`` via ``session.merge()`` (PK-based).
        3. Delete-then-insert ``EHRRecord`` rows for this patient.
        4. Delete-then-insert ``WearableDay`` rows for this patient.

        All operations use the same ``session``; the batch commit in
        :meth:`ingest` flushes periodically.
        """
        session = self._session
        patient = patient_data.patient
        pid = patient.patient_id

        # 1. Upsert Patient (merge on PK)
        await session.merge(patient)

        # 2. Upsert LifestyleProfile (merge on PK)
        if patient_data.lifestyle is not None:
            await session.merge(patient_data.lifestyle)

        # 3. Delete-then-insert EHR records (idempotent per patient).
        # Delete always runs so stale records are cleared even on empty re-ingest.
        await session.execute(
            delete(EHRRecord).where(EHRRecord.patient_id == pid)  # type: ignore[arg-type]
        )
        for record in patient_data.ehr_records:
            session.add(record)

        # 4. Delete-then-insert wearable days (idempotent per patient).
        # Delete always runs so stale days are cleared even on empty re-ingest.
        await session.execute(
            delete(WearableDay).where(WearableDay.patient_id == pid)  # type: ignore[arg-type]
        )
        for day in patient_data.wearable_days:
            session.add(day)

        # Flush after each patient so FK constraints are satisfied before
        # child rows are inserted in the same unit of work
        await session.flush()

    # -----------------------------------------------------------------------
    # Embedding helpers
    # -----------------------------------------------------------------------

    async def _embed_all_records(self) -> None:
        """Fetch all EHRRecord rows with null embeddings and embed them in batches.

        Calls ``LLMProvider.embed`` with up to ``_EMBED_BATCH_SIZE`` texts at a
        time.  Updates each row's ``embedding`` column in-place via the session.

        Rows that already have a non-null embedding are skipped — this makes
        repeated calls idempotent.
        """
        assert self._llm_provider is not None  # guarded by caller

        session = self._session

        # Load all records that still need embeddings.
        stmt = select(EHRRecord).where(
            getattr(EHRRecord, "embedding").is_(None)  # noqa: B009  # mypy-strict pattern: see CLAUDE.md
        )
        result = await session.execute(stmt)
        records = list(result.scalars().all())

        if not records:
            return

        _logger.info(
            "embedding ehr_records",
            extra={"record_count": len(records)},
        )

        # Batch the embedding calls to avoid oversized requests.
        for batch_start in range(0, len(records), _EMBED_BATCH_SIZE):
            batch = records[batch_start : batch_start + _EMBED_BATCH_SIZE]
            texts = [_record_to_text(r) for r in batch]
            vectors = await self._llm_provider.embed(texts)

            for record, vector in zip(batch, vectors, strict=True):
                record.embedding = vector

            # Flush after each batch so memory is bounded.
            await session.flush()

        _logger.info(
            "embedding complete",
            extra={"record_count": len(records)},
        )


def _record_to_text(record: EHRRecord) -> str:
    """Build a plain-text representation of an EHRRecord for embedding.

    Produces a short, information-dense string from ``record_type`` and
    ``payload`` that captures the clinical semantics of the record.

    Args:
        record: An ``EHRRecord`` instance.

    Returns:
        A text string suitable for passing to an embedding model.
    """
    try:
        payload_str = json.dumps(record.payload, ensure_ascii=False)
    except (TypeError, ValueError):
        payload_str = str(record.payload)

    return f"{record.record_type}: {payload_str}"
