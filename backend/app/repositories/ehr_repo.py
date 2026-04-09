"""EHRRepository — patient-scoped access to EHRRecord rows.

Inherits from ``PatientScopedRepository[EHRRecord]`` for the base ``get`` and
``list`` semantics, and adds the ordering + optional ``record_type`` filter
that the API layer needs.

Stack: SQLAlchemy 2.0 async, sqlalchemy.select() + session.execute().
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ehr_record import EHRRecord
from app.repositories.base import PatientScopedRepository

# SQLModel generates mapped attributes whose __eq__ returns a Python bool at
# the Python level, but a ColumnElement at runtime.  mypy strict mode rejects
# Model.col == value in .where() because it infers bool.  We retrieve the
# attribute via getattr() (typed Any) so mypy accepts the expression while
# the generated SQL is identical.  This pattern mirrors the base repository.
_PID = "patient_id"
_TYPE = "record_type"
_ID = "id"
_RECORDED_AT = "recorded_at"


class EHRRepository(PatientScopedRepository[EHRRecord]):
    """Async repository for EHRRecord — enforces patient_id isolation.

    Every query filters ``WHERE patient_id = :pid`` at the SQL level.
    Cross-patient reads are structurally impossible: patient_id is a required
    argument on every public method.

    Usage::

        repo = EHRRepository(session)
        records = await repo.list(patient_id="PT0001")
        lab = await repo.list(patient_id="PT0001", record_type="lab_panel")
        single = await repo.get(patient_id="PT0001", record_id=42)
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session, model=EHRRecord)

    async def list(  # type: ignore[override]
        self,
        *,
        patient_id: str,
        record_type: str | None = None,
    ) -> list[EHRRecord]:
        """List EHR records for a patient, ordered by ``recorded_at DESC``.

        Args:
            patient_id:  The patient whose records are in scope (required).
            record_type: Optional filter — one of "condition", "medication",
                         "visit", or "lab_panel".  Omit to return all types.

        Returns:
            A list of ``EHRRecord`` instances, newest first.
        """
        pid_attr = getattr(EHRRecord, _PID)
        recorded_at_attr = getattr(EHRRecord, _RECORDED_AT)

        stmt = (
            select(EHRRecord)
            .where(pid_attr == patient_id)
            .order_by(recorded_at_attr.desc())
        )

        if record_type is not None:
            type_attr = getattr(EHRRecord, _TYPE)
            stmt = stmt.where(type_attr == record_type)

        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get(  # type: ignore[override]
        self,
        *,
        patient_id: str,
        record_id: int,
    ) -> EHRRecord | None:
        """Fetch a single EHRRecord by ``patient_id`` + surrogate ``id``.

        Returns ``None`` if the record does not exist or belongs to a
        different patient.  Cross-patient access is impossible because the
        ``WHERE patient_id = :pid`` clause is always present.

        Args:
            patient_id: The patient whose records are in scope.
            record_id:  The surrogate ``id`` (auto-increment PK) of the record.

        Returns:
            The matching ``EHRRecord``, or ``None``.
        """
        pid_attr = getattr(EHRRecord, _PID)
        id_attr = getattr(EHRRecord, _ID)

        stmt = (
            select(EHRRecord)
            .where(pid_attr == patient_id)
            .where(id_attr == record_id)
        )
        result = await self._session.execute(stmt)
        return result.scalars().first()
