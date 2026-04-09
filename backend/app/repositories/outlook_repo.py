"""VitalityOutlookRepository — patient-scoped access to VitalityOutlook rows.

``upsert_by_horizon`` maintains one row per (patient_id, horizon_months) by
checking for an existing row and either updating it or inserting a new one.
The VitalityOutlook model does not carry a unique constraint on
(patient_id, horizon_months), so a Postgres ON CONFLICT upsert cannot be used
directly.  The select-then-update approach achieves the same idempotent
semantics within a single transaction.

Stack: SQLAlchemy 2.0 async (select() + session.execute()), SQLModel table models.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.vitality_outlook import VitalityOutlook
from app.repositories.base import PatientScopedRepository

# SQLModel generates mapped attributes whose __eq__ returns a Python bool at
# the Python level, but a ColumnElement at runtime.  mypy strict mode rejects
# Model.col == value in .where() because it infers bool.  We retrieve the
# attribute via getattr() (typed Any) so mypy accepts the expression while
# the generated SQL is identical.  This pattern mirrors the base repository.
_PID = "patient_id"
_HORIZON = "horizon_months"
_COMPUTED_AT = "computed_at"
_ID = "id"


class VitalityOutlookRepository(PatientScopedRepository[VitalityOutlook]):
    """Async repository for VitalityOutlook — enforces patient_id isolation.

    Maintains at most one outlook row per (patient_id, horizon_months)
    combination via Postgres upsert semantics.  Use ``latest`` to retrieve
    the current projection for a horizon; use ``upsert_by_horizon`` to
    atomically insert or refresh the projection.

    Usage::

        repo = VitalityOutlookRepository(session)
        o = await repo.upsert_by_horizon(patient_id="PT0001", outlook=vo)
        latest = await repo.latest(patient_id="PT0001", horizon_months=3)
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session, model=VitalityOutlook)

    async def upsert_by_horizon(
        self, *, patient_id: str, outlook: VitalityOutlook
    ) -> VitalityOutlook:
        """Insert or update a VitalityOutlook for a (patient_id, horizon_months) pair.

        Maintains at most one row per (patient_id, horizon_months) using a
        select-then-update pattern within the current transaction.  If an
        existing row is found it is updated in place; otherwise a new row is
        inserted.

        The ``patient_id`` argument is the authoritative owner: it is always
        written to the row regardless of what ``outlook.patient_id`` contains.

        Args:
            patient_id: The patient this outlook belongs to.
            outlook:    The VitalityOutlook to persist.

        Returns:
            The persisted VitalityOutlook instance.
        """
        # Check for an existing row for this (patient_id, horizon_months) pair.
        existing = await self.latest(
            patient_id=patient_id, horizon_months=outlook.horizon_months
        )

        if existing is not None:
            # Update the existing row in place.
            object.__setattr__(existing, "projected_score", outlook.projected_score)
            object.__setattr__(existing, "narrative", outlook.narrative)
            object.__setattr__(existing, "computed_at", outlook.computed_at)
            await self._session.flush()
            return existing

        # No existing row — insert a new one.
        object.__setattr__(outlook, "patient_id", patient_id)
        self._session.add(outlook)
        await self._session.flush()
        return outlook

    async def latest(
        self, *, patient_id: str, horizon_months: int
    ) -> VitalityOutlook | None:
        """Fetch the most recently computed outlook for a patient + horizon.

        Args:
            patient_id:     The patient whose outlook is in scope.
            horizon_months: The projection horizon (3, 6, or 12).

        Returns:
            The most recent VitalityOutlook for this horizon, or ``None``.
        """
        pid_attr = getattr(VitalityOutlook, _PID)
        horizon_attr = getattr(VitalityOutlook, _HORIZON)
        computed_at_attr = getattr(VitalityOutlook, _COMPUTED_AT)

        stmt = (
            select(VitalityOutlook)
            .where(pid_attr == patient_id)
            .where(horizon_attr == horizon_months)
            .order_by(computed_at_attr.desc())
        )
        result = await self._session.execute(stmt)
        return result.scalars().first()
