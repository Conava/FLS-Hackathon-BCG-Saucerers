"""VitalityRepository — patient-scoped access to VitalitySnapshot.

One row per patient.  The ``upsert`` method uses Postgres
``INSERT … ON CONFLICT (patient_id) DO UPDATE`` to atomically insert or
refresh the snapshot — safe for concurrent writes and idempotent ingestion.

Stack: SQLAlchemy 2.0 async, ``sqlalchemy.dialects.postgresql.insert``.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.vitality_snapshot import VitalitySnapshot

# SQLModel generates mapped attributes whose __eq__ returns a Python bool at
# the Python level, but a ColumnElement at runtime.  mypy strict mode rejects
# Model.col == value in .where() because it infers bool.  We retrieve the
# attribute via getattr() (typed Any) so mypy accepts the expression while
# the generated SQL is identical.  This pattern mirrors the base repository.
_PID = "patient_id"


class VitalityRepository:
    """Async repository for VitalitySnapshot — enforces patient_id isolation.

    Because VitalitySnapshot uses ``patient_id`` as its sole PK (identical
    shape to Patient), this class is a thin dedicated repository rather than
    an inheritor of ``PatientScopedRepository``.  Every query explicitly
    includes ``WHERE patient_id = :pid``.

    Usage::

        repo = VitalityRepository(session)
        snap = await repo.upsert(patient_id="PT0001", snapshot=vs)
        snap = await repo.get(patient_id="PT0001")
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, *, patient_id: str) -> VitalitySnapshot | None:
        """Fetch the current VitalitySnapshot for a patient.

        Args:
            patient_id: The patient whose snapshot is in scope.

        Returns:
            The ``VitalitySnapshot`` instance, or ``None`` if not yet computed.
        """
        pid_attr = getattr(VitalitySnapshot, _PID)
        stmt = select(VitalitySnapshot).where(pid_attr == patient_id)
        result = await self._session.execute(stmt)
        return result.scalars().first()

    async def upsert(
        self, *, patient_id: str, snapshot: VitalitySnapshot
    ) -> VitalitySnapshot:
        """Insert or update a VitalitySnapshot for a patient.

        Uses Postgres ``INSERT … ON CONFLICT (patient_id) DO UPDATE`` so this
        is safe on re-compute — never raises a duplicate-key error.

        The ``patient_id`` argument is the authoritative owner: it is always
        written to the row regardless of what ``snapshot.patient_id`` contains.
        This is the same defensive-set invariant as in
        ``PatientScopedRepository.upsert``.

        Args:
            patient_id: The patient this snapshot belongs to.
            snapshot:   The ``VitalitySnapshot`` to persist.

        Returns:
            The persisted ``VitalitySnapshot`` instance (re-fetched after upsert).
        """
        # Build the values dict from the snapshot, overriding patient_id.
        values: dict[str, Any] = {
            "patient_id": patient_id,
            "computed_at": snapshot.computed_at,
            "score": snapshot.score,
            "subscores": snapshot.subscores,
            "risk_flags": snapshot.risk_flags,
        }

        # Columns to update on conflict — everything except the PK itself.
        update_values: dict[str, Any] = {
            "computed_at": snapshot.computed_at,
            "score": snapshot.score,
            "subscores": snapshot.subscores,
            "risk_flags": snapshot.risk_flags,
        }

        stmt = (
            pg_insert(VitalitySnapshot)
            .values(**values)
            .on_conflict_do_update(
                index_elements=["patient_id"],
                set_=update_values,
            )
        )
        await self._session.execute(stmt)
        await self._session.flush()

        # Re-fetch to return a fully-populated ORM instance.
        persisted = await self.get(patient_id=patient_id)
        if persisted is None:
            raise RuntimeError(
                f"upsert succeeded but subsequent get returned None for {patient_id!r}"
            )
        return persisted
