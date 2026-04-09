"""SurveyRepository — patient-scoped access to SurveyResponse rows.

Stack: SQLAlchemy 2.0 async (select() + session.execute()), SQLModel table models.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.survey_response import SurveyResponse
from app.repositories.base import PatientScopedRepository

# SQLModel generates mapped attributes whose __eq__ returns a Python bool at
# the Python level, but a ColumnElement at runtime.  mypy strict mode rejects
# Model.col == value in .where() because it infers bool.  We retrieve the
# attribute via getattr() (typed Any) so mypy accepts the expression while
# the generated SQL is identical.  This pattern mirrors the base repository.
_PID = "patient_id"
_KIND = "kind"
_SUBMITTED_AT = "submitted_at"
_ID = "id"


class SurveyRepository(PatientScopedRepository[SurveyResponse]):
    """Async repository for SurveyResponse — enforces patient_id isolation.

    Every query filters ``WHERE patient_id = :pid`` at the SQL level.
    Cross-patient reads are structurally impossible.

    Usage::

        repo = SurveyRepository(session)
        s = await repo.create(patient_id="PT0001", survey=sr)
        latest = await repo.latest_by_kind(patient_id="PT0001", kind="weekly")
        history = await repo.history(patient_id="PT0001", kind="weekly")
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session, model=SurveyResponse)

    async def create(
        self, *, patient_id: str, survey: SurveyResponse
    ) -> SurveyResponse:
        """Persist a new SurveyResponse row, defensively setting patient_id.

        Args:
            patient_id: The patient this survey belongs to.
            survey:     The SurveyResponse instance to persist.

        Returns:
            The persisted SurveyResponse instance with id populated.
        """
        # Defensive set — overwrites whatever the caller placed on the object.
        object.__setattr__(survey, "patient_id", patient_id)
        self._session.add(survey)
        await self._session.flush()
        return survey

    async def latest_by_kind(
        self, *, patient_id: str, kind: str
    ) -> SurveyResponse | None:
        """Fetch the most recently submitted survey of a given kind.

        Args:
            patient_id: The patient whose surveys are in scope.
            kind:       One of "onboarding", "weekly", or "quarterly".

        Returns:
            The most recent SurveyResponse for this kind, or ``None``.
        """
        pid_attr = getattr(SurveyResponse, _PID)
        kind_attr = getattr(SurveyResponse, _KIND)
        submitted_at_attr = getattr(SurveyResponse, _SUBMITTED_AT)

        stmt = (
            select(SurveyResponse)
            .where(pid_attr == patient_id)
            .where(kind_attr == kind)
            .order_by(submitted_at_attr.desc())
        )
        result = await self._session.execute(stmt)
        return result.scalars().first()

    async def history(
        self, *, patient_id: str, kind: str
    ) -> list[SurveyResponse]:
        """Return all submitted surveys of a given kind for a patient.

        Rows are ordered by ``submitted_at DESC`` so index 0 is the most recent.

        Args:
            patient_id: The patient whose surveys are in scope.
            kind:       One of "onboarding", "weekly", or "quarterly".

        Returns:
            A list of SurveyResponse instances, newest first.
        """
        pid_attr = getattr(SurveyResponse, _PID)
        kind_attr = getattr(SurveyResponse, _KIND)
        submitted_at_attr = getattr(SurveyResponse, _SUBMITTED_AT)

        stmt = (
            select(SurveyResponse)
            .where(pid_attr == patient_id)
            .where(kind_attr == kind)
            .order_by(submitted_at_attr.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
