"""SQLModel entity: SurveyResponse.

Stores the raw answers for each survey completion. Three survey kinds exist:
  - onboarding: ~12 questions taken once on first login; bootstraps the
    LifestyleProfile and Protocol generator.
  - weekly: 3-question micro-survey (energy, changes, protocol fit); drives
    mid-week protocol adjustments.
  - quarterly: full re-survey with side-by-side Score / Outlook deltas; natural
    commerce moment.

Answers are stored as JSONB (arbitrary key-value map) AND the structured
LifestyleProfile fields are updated in the same transaction (see SurveyRouter).
An embedding column is reserved for RAG retrieval by the Coach.
"""

from __future__ import annotations

import datetime
from typing import Any

from sqlalchemy import Column, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

try:
    from pgvector.sqlalchemy import Vector  # type: ignore[import-untyped]
    _VECTOR_AVAILABLE = True
except ImportError:
    _VECTOR_AVAILABLE = False


def _utcnow() -> datetime.datetime:
    """Return current UTC time as timezone-naive datetime (CLAUDE.md pattern)."""
    return datetime.datetime.now(datetime.UTC).replace(tzinfo=None)


class SurveyResponse(SQLModel, table=True):
    """One survey submission by a patient.

    ``kind`` discriminates the three survey types:
      "onboarding" | "weekly" | "quarterly"
    """

    __tablename__ = "survey_response"

    # Named index on patient_id — do NOT add index=True to Field below.
    __table_args__ = (Index("ix_survey_response_patient_id", "patient_id"),)

    id: int | None = Field(default=None, primary_key=True)

    # Patient isolation boundary — indexed via __table_args__
    patient_id: str = Field(foreign_key="patient.patient_id")

    # Survey type discriminator
    kind: str  # "onboarding" | "weekly" | "quarterly"

    # Free-form answer map (typed at the service layer, stored raw here)
    answers: dict[str, Any] = Field(sa_column=Column(JSONB, nullable=False))

    # When the patient submitted the survey (naive UTC)
    submitted_at: datetime.datetime

    # Optional embedding — populated by the RAG layer for Coach retrieval
    # Vector(768) matches text-embedding-004 dimensionality
    embedding: list[float] | None = Field(
        default=None,
        sa_column=Column(
            Vector(768) if _VECTOR_AVAILABLE else JSONB,
            nullable=True,
        ),
    )
