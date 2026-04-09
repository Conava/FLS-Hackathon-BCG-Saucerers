"""SQLModel entity: ClinicalReview.

Represents a clinician review request for a patient. Created when the AI
surfaces a risk flag that requires human review (e.g. elevated ApoB, abnormal
ECG pattern). A clinician is assigned via ``clinician_id``.

Status lifecycle:
  "pending"    — review request created; awaiting clinician assignment
  "in_review"  — clinician has opened the case
  "resolved"   — clinician has completed the review (follow-up may be booked)

``ai_flag`` stores the structured AI-generated risk context that triggered the
review request (JSONB, nullable). It is NOT shown to the patient directly.
Only wellness-framed summaries are surfaced in the UI.
"""

from __future__ import annotations

import datetime
from typing import Any

from sqlalchemy import Column, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


def _utcnow() -> datetime.datetime:
    """Return current UTC time as timezone-naive datetime (CLAUDE.md pattern)."""
    return datetime.datetime.now(datetime.UTC).replace(tzinfo=None)


class ClinicalReview(SQLModel, table=True):
    """A clinician review request triggered by an AI-surfaced risk flag."""

    __tablename__ = "clinical_review"

    # Named index on patient_id — do NOT add index=True to Field below.
    __table_args__ = (Index("ix_clinical_review_patient_id", "patient_id"),)

    id: int | None = Field(default=None, primary_key=True)

    # Patient isolation boundary — indexed via __table_args__
    patient_id: str = Field(foreign_key="patient.patient_id")

    # Human-readable reason for the review request (wellness-framed, not diagnostic)
    reason: str

    # Structured AI flag context (internal; not shown to patient)
    # E.g. {"signal": "elevated_apob", "severity": "moderate", "ehr_record_ids": [...]}
    ai_flag: dict[str, Any] | None = Field(
        default=None, sa_column=Column(JSONB, nullable=True)
    )

    # Review status: "pending" | "in_review" | "resolved"
    status: str

    # Optional assigned clinician (external ID from the provider system)
    clinician_id: str | None = Field(default=None)

    # When this review was created (naive UTC)
    created_at: datetime.datetime = Field(default_factory=_utcnow)
