"""ProtocolRepository and ProtocolActionRepository.

IMPORTANT — ProtocolAction isolation contract:
  ProtocolAction has NO ``patient_id`` column.  Patient isolation is enforced
  by a two-step query:
    1. Collect the set of protocol IDs that belong to the requesting patient:
           SELECT id FROM protocol WHERE patient_id = :pid
    2. Use that set to scope the protocol_action query:
           SELECT * FROM protocol_action WHERE protocol_id IN (...)
  A bare ``WHERE protocol_id = :x`` without first confirming the protocol
  belongs to the patient would allow cross-patient data access.  Never bypass
  this two-step pattern.

Stack: SQLAlchemy 2.0 async (select() + session.execute()), SQLModel table models.
"""

from __future__ import annotations

from sqlalchemy import nullslast, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.protocol import Protocol, ProtocolAction
from app.repositories.base import PatientScopedRepository

# SQLModel generates mapped attributes whose __eq__ returns a Python bool at
# the Python level, but a ColumnElement at runtime.  mypy strict mode rejects
# Model.col == value in .where() because it infers bool.  We retrieve the
# attribute via getattr() (typed Any) so mypy accepts the expression while
# the generated SQL is identical.  This pattern mirrors the base repository.
_PID = "patient_id"
_STATUS = "status"
_ID = "id"
_PROTOCOL_ID = "protocol_id"
_STREAK_DAYS = "streak_days"
_COMPLETED_TODAY = "completed_today"
_SORT_ORDER = "sort_order"
_SKIPPED_TODAY = "skipped_today"
_SKIP_REASON = "skip_reason"


class ProtocolRepository(PatientScopedRepository[Protocol]):
    """Async repository for Protocol — enforces patient_id isolation.

    Every query filters ``WHERE patient_id = :pid`` at the SQL level.
    Cross-patient reads are structurally impossible.

    Usage::

        repo = ProtocolRepository(session)
        protocol = await repo.create(patient_id="PT0001", protocol=p)
        active = await repo.get_active(patient_id="PT0001")
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session, model=Protocol)

    async def create(self, *, patient_id: str, protocol: Protocol) -> Protocol:
        """Persist a new Protocol row, defensively setting patient_id.

        Args:
            patient_id: The patient this protocol belongs to.
            protocol:   The Protocol instance to persist.

        Returns:
            The persisted Protocol instance with id populated.
        """
        # Defensive set — overwrites whatever the caller placed on the object.
        object.__setattr__(protocol, "patient_id", patient_id)
        self._session.add(protocol)
        await self._session.flush()
        return protocol

    async def get(  # type: ignore[override]
        self,
        *,
        patient_id: str,
        record_id: int,
    ) -> Protocol | None:
        """Fetch a single Protocol by patient_id + id.

        Returns ``None`` if the record does not exist or belongs to a
        different patient.

        Args:
            patient_id: The patient whose records are in scope.
            record_id:  The surrogate id (auto-increment PK) of the record.

        Returns:
            The matching Protocol, or ``None``.
        """
        pid_attr = getattr(Protocol, _PID)
        id_attr = getattr(Protocol, _ID)

        stmt = (
            select(Protocol)
            .where(pid_attr == patient_id)
            .where(id_attr == record_id)
        )
        result = await self._session.execute(stmt)
        return result.scalars().first()

    async def list(  # type: ignore[override]
        self,
        *,
        patient_id: str,
    ) -> list[Protocol]:
        """List all Protocol rows for a patient, ordered by id DESC.

        Args:
            patient_id: The patient whose records are in scope.

        Returns:
            A list of Protocol instances, newest first.
        """
        pid_attr = getattr(Protocol, _PID)
        id_attr = getattr(Protocol, _ID)

        stmt = (
            select(Protocol)
            .where(pid_attr == patient_id)
            .order_by(id_attr.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_active(self, *, patient_id: str) -> Protocol | None:
        """Fetch the current active Protocol for a patient.

        Returns the most recently created protocol with status="active", or
        ``None`` if no active protocol exists.

        Args:
            patient_id: The patient whose active protocol is in scope.

        Returns:
            The active Protocol, or ``None``.
        """
        pid_attr = getattr(Protocol, _PID)
        status_attr = getattr(Protocol, _STATUS)
        id_attr = getattr(Protocol, _ID)

        stmt = (
            select(Protocol)
            .where(pid_attr == patient_id)
            .where(status_attr == "active")
            .order_by(id_attr.desc())
        )
        result = await self._session.execute(stmt)
        return result.scalars().first()


class ProtocolActionRepository:
    """Async repository for ProtocolAction — isolation via Protocol parent.

    ProtocolAction has NO ``patient_id`` column.  Every query MUST first
    resolve the set of Protocol IDs that belong to the requesting patient,
    then scope the ProtocolAction query to that set.  This is the two-step
    isolation pattern described in the module docstring.

    Direct access by ``protocol_id`` alone (without first confirming the
    protocol belongs to the patient) is forbidden.

    Usage::

        repo = ProtocolActionRepository(session)
        action = await repo.add(action=a)
        actions = await repo.list_for_patient(patient_id="PT0001")
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, *, action: ProtocolAction) -> ProtocolAction:
        """Persist a new ProtocolAction row.

        The caller is responsible for setting the correct ``protocol_id``.
        Callers must have previously confirmed (via ProtocolRepository) that
        the parent protocol belongs to the intended patient.

        Args:
            action: The ProtocolAction instance to persist.

        Returns:
            The persisted ProtocolAction instance with id populated.
        """
        self._session.add(action)
        await self._session.flush()
        return action

    async def list_for_patient(
        self, *, patient_id: str
    ) -> list[ProtocolAction]:
        """List all ProtocolAction rows for a patient.

        Enforces isolation via two-step subquery:
          SELECT * FROM protocol_action
          WHERE protocol_id IN (
            SELECT id FROM protocol WHERE patient_id = :pid
          )

        No bare ``WHERE protocol_id = :x`` is used here — the Protocol
        subquery ensures patient ownership.

        Args:
            patient_id: The patient whose actions are in scope.

        Returns:
            A list of ProtocolAction instances (may be empty).
        """
        # Step 1: collect protocol IDs that belong to this patient.
        pid_attr = getattr(Protocol, _PID)
        protocol_id_attr = getattr(Protocol, _ID)
        protocol_ids_subq = (
            select(protocol_id_attr)
            .where(pid_attr == patient_id)
            .scalar_subquery()
        )

        # Step 2: scope ProtocolAction to those protocol IDs, ordered deterministically.
        # sort_order NULLS LAST keeps unordered rows at the end; id ASC breaks ties.
        action_protocol_id_attr = getattr(ProtocolAction, _PROTOCOL_ID)
        sort_order_attr = getattr(ProtocolAction, _SORT_ORDER)
        action_id_attr = getattr(ProtocolAction, _ID)
        stmt = (
            select(ProtocolAction)
            .where(action_protocol_id_attr.in_(protocol_ids_subq))
            .order_by(nullslast(sort_order_attr.asc()), action_id_attr.asc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_for_patient(
        self, *, patient_id: str, action_id: int
    ) -> ProtocolAction | None:
        """Fetch a single ProtocolAction by id, scoped to a patient.

        Uses the two-step isolation pattern (Protocol subquery → action).
        Returns ``None`` if the action does not exist or the parent protocol
        belongs to a different patient.

        Args:
            patient_id: The patient whose actions are in scope.
            action_id:  The surrogate id of the ProtocolAction.

        Returns:
            The matching ProtocolAction, or ``None``.
        """
        # Step 1: collect protocol IDs that belong to this patient.
        pid_attr = getattr(Protocol, _PID)
        protocol_id_attr = getattr(Protocol, _ID)
        protocol_ids_subq = (
            select(protocol_id_attr)
            .where(pid_attr == patient_id)
            .scalar_subquery()
        )

        # Step 2: scope ProtocolAction to those protocol IDs AND the given id.
        action_id_attr = getattr(ProtocolAction, _ID)
        action_protocol_id_attr = getattr(ProtocolAction, _PROTOCOL_ID)
        stmt = (
            select(ProtocolAction)
            .where(action_protocol_id_attr.in_(protocol_ids_subq))
            .where(action_id_attr == action_id)
        )
        result = await self._session.execute(stmt)
        return result.scalars().first()

    async def update_streak(
        self,
        *,
        patient_id: str,
        action_id: int,
        streak_days: int,
        completed_today: bool,
    ) -> ProtocolAction | None:
        """Update streak_days and completed_today for a ProtocolAction.

        First confirms the action belongs to a protocol owned by the patient
        (two-step isolation), then updates the fields in place.

        Args:
            patient_id:     The patient whose action is being updated.
            action_id:      The surrogate id of the ProtocolAction.
            streak_days:    New streak day count.
            completed_today: Whether the action was completed today.

        Returns:
            The updated ProtocolAction, or ``None`` if not found / not owned.
        """
        action = await self.get_for_patient(
            patient_id=patient_id, action_id=action_id
        )
        if action is None:
            return None

        object.__setattr__(action, "streak_days", streak_days)
        object.__setattr__(action, "completed_today", completed_today)
        # Completing an action clears any existing skip flag (independent flags).
        object.__setattr__(action, "skipped_today", False)
        object.__setattr__(action, "skip_reason", None)
        await self._session.flush()
        return action

    async def update_skip(
        self,
        *,
        patient_id: str,
        action_id: int,
        reason: str,
    ) -> ProtocolAction | None:
        """Set skipped_today=True and record the skip reason for a ProtocolAction.

        Confirms ownership via the two-step isolation pattern.  Does NOT touch
        streak_days or completed_today — skip and complete are independent flags.

        Args:
            patient_id: The patient whose action is being skipped.
            action_id:  The surrogate id of the ProtocolAction.
            reason:     Human-readable reason for skipping today.

        Returns:
            The updated ProtocolAction, or ``None`` if not found / not owned.
        """
        action = await self.get_for_patient(
            patient_id=patient_id, action_id=action_id
        )
        if action is None:
            return None

        object.__setattr__(action, "skipped_today", True)
        object.__setattr__(action, "skip_reason", reason)
        await self._session.flush()
        return action

    async def update_sort_orders(
        self,
        *,
        patient_id: str,
        ordered_ids: list[int],
    ) -> list[ProtocolAction]:
        """Assign sort_order to each action based on its position in ordered_ids.

        Verifies every action in ordered_ids belongs to the patient (two-step
        isolation).  Raises ValueError if any action is not owned by patient_id.
        Returns the reordered list in the new order.

        Args:
            patient_id:  The patient whose actions are being reordered.
            ordered_ids: Action ids in the desired display order (1-indexed positions).

        Returns:
            List of updated ProtocolAction instances in the new order.

        Raises:
            ValueError: If any action_id is not found for this patient.
        """
        updated: list[ProtocolAction] = []
        for position, action_id in enumerate(ordered_ids, start=1):
            action = await self.get_for_patient(
                patient_id=patient_id, action_id=action_id
            )
            if action is None:
                raise ValueError(
                    f"ProtocolAction {action_id!r} not found for patient {patient_id!r}."
                )
            object.__setattr__(action, "sort_order", position)
            updated.append(action)
        await self._session.flush()
        return updated
