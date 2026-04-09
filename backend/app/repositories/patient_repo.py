"""PatientRepository — fetch Patient records by patient_id.

Because the Patient table uses ``patient_id`` as its own primary key (not a
child-table FK), this repository composes rather than inherits
``PatientScopedRepository``.  The ``WHERE patient_id = :pid`` invariant is
still enforced explicitly in every query — it is never delegated to the caller.

Stack: SQLAlchemy 2.0 async (select + session.execute().scalars()).
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.patient import Patient

# SQLModel generates mapped attributes whose __eq__ returns a Python bool at
# the Python level, but a ColumnElement at runtime.  mypy strict mode rejects
# Model.col == value in .where() because it infers bool.  We retrieve the
# attribute via getattr() (typed Any) so mypy accepts the expression while
# the generated SQL is identical.  This pattern mirrors the base repository.
_PID = "patient_id"


class PatientRepository:
    """Async repository for the Patient entity.

    Unlike child-table repositories, Patient's PK *is* patient_id.  Composing
    PatientScopedRepository would still work, but the "second PK column"
    helper in the base returns the patient_id column itself — which means the
    base ``.get(patient_id, record_id)`` would require passing patient_id
    twice.  This thin dedicated repository is cleaner.

    Every method enforces ``WHERE patient_id = :pid`` at the SQL level.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, *, patient_id: str) -> Patient | None:
        """Fetch a Patient by their primary-key ``patient_id``.

        Returns ``None`` if no patient with the given id exists.  The method
        is keyword-only (``*``) so callers cannot accidentally omit the label.

        Args:
            patient_id: The patient's unique identifier (e.g. "PT0001").

        Returns:
            The matching ``Patient`` instance, or ``None``.
        """
        pid_attr = getattr(Patient, _PID)
        stmt = select(Patient).where(pid_attr == patient_id)
        result = await self._session.execute(stmt)
        return result.scalars().first()
