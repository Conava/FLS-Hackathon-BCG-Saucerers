"""PatientScopedRepository — hard patient_id isolation for every SQL query.

This is the GDPR hard-isolation invariant: every query method on every
repository injects ``WHERE patient_id = :pid`` at the SQL level.  Direct
cross-patient access is structurally impossible — not just conventional.

Pitch talking point (docs/08-legal-compliance.md):
  "SQL-level patient_id on every query — GDPR Art. 9 isolation by
   construction, not convention."

Usage::

    class EHRRepository(PatientScopedRepository[EHRRecord]):
        async def list_by_type(
            self, patient_id: str, *, record_type: str
        ) -> list[EHRRecord]:
            return await self.list(patient_id=patient_id, record_type=record_type)

Stack: SQLAlchemy 2.0 async (select() + session.execute()), SQLModel table models.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import inspect, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import SQLModel


class PatientScopedRepository[ModelT: SQLModel]:
    """Generic async repository that enforces patient_id isolation on every query.

    Every public method accepts ``patient_id`` as a required positional
    argument and injects ``WHERE patient_id = :pid`` into the generated SQL.
    No method allows callers to retrieve records without specifying a
    patient_id — the signature makes it a type error.

    Args:
        session: An open ``AsyncSession`` (injected by FastAPI / test fixture).
        model:   The concrete SQLModel table class (e.g. ``EHRRecord``).
    """

    def __init__(self, session: AsyncSession, model: type[ModelT]) -> None:
        self._session = session
        self._model = model

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _pk_column(self) -> Any:
        """Return the non-patient_id primary key column for the model.

        For simple PK tables (e.g. EHRRecord with ``id`` int PK) this
        returns that column.  For composite PKs (e.g. WearableDay with
        ``(patient_id, date)``) it returns the first PK column that is
        NOT ``patient_id``.

        Returns the patient_id column itself only if there is no other PK
        (i.e. for single-column PK tables like Patient, VitalitySnapshot).
        """
        mapper = inspect(self._model)
        if mapper is None:
            raise RuntimeError(f"SQLAlchemy inspect() returned None for {self._model!r}")
        pk_cols = [col for col in mapper.primary_key]

        non_patient_pks = [col for col in pk_cols if col.name != "patient_id"]
        if non_patient_pks:
            return non_patient_pks[0]

        # Fallback: single-column PK is patient_id itself (Patient table)
        return pk_cols[0]

    # ------------------------------------------------------------------
    # Public API — patient_id is always the first positional argument
    # ------------------------------------------------------------------

    async def get(self, patient_id: str, record_id: Any) -> ModelT | None:
        """Fetch a single record by its primary key, scoped to patient_id.

        Returns ``None`` if the record does not exist or belongs to a
        different patient.  Cross-patient reads are impossible because the
        ``WHERE patient_id = :pid`` clause is always present.

        Args:
            patient_id: The patient whose records are in scope.
            record_id:  The value of the non-patient_id primary key column.

        Returns:
            The matching model instance, or ``None``.
        """
        pk_col = self._pk_column()
        model_pk_attr = getattr(self._model, pk_col.name)
        _pid_attr_name = "patient_id"
        model_pid_attr = getattr(self._model, _pid_attr_name)

        stmt = (
            select(self._model)
            .where(model_pid_attr == patient_id)
            .where(model_pk_attr == record_id)
        )
        result = await self._session.execute(stmt)
        return result.scalars().first()

    async def list(self, patient_id: str, **filters: Any) -> list[ModelT]:
        """List records for a patient, optionally filtered by extra columns.

        Args:
            patient_id: The patient whose records are in scope.
            **filters:  Additional column equality filters; kwargs map to
                        ``getattr(model, key) == value``.  Unrecognised
                        attribute names raise ``AttributeError`` at query time.

        Returns:
            A list of matching model instances (may be empty).
        """
        _pid_attr_name = "patient_id"
        model_pid_attr = getattr(self._model, _pid_attr_name)
        stmt = select(self._model).where(model_pid_attr == patient_id)

        for key, value in filters.items():
            col_attr = getattr(self._model, key)
            stmt = stmt.where(col_attr == value)

        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def upsert(self, patient_id: str, obj: ModelT) -> ModelT:
        """Persist or update a record, defensively setting patient_id.

        Sets ``obj.patient_id = patient_id`` before merging, ensuring the
        stored row always belongs to the declared patient regardless of what
        the caller placed on the object.

        Uses ``session.merge()`` which performs INSERT … ON CONFLICT UPDATE
        semantics at the SQLAlchemy identity-map level: if a row with the
        same PK already exists in the session or the DB it is updated,
        otherwise a new row is inserted.

        Args:
            patient_id: The patient this record belongs to.
            obj:        The model instance to persist.

        Returns:
            The merged (possibly newly-created) model instance.
        """
        # Defensive set — overwrites whatever the caller placed on the object.
        # ModelT is bound to SQLModel; patient_id is a str field on all child models.
        object.__setattr__(obj, "patient_id", patient_id)

        merged = await self._session.merge(obj)
        await self._session.flush()
        return merged
