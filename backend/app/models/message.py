"""SQLModel entity: Message.

In-app messages between a patient and their care team (clinician / care
coordinator). Used by the Care → Messages surface.

The ``sender`` field discriminates direction:
  "patient"   — message sent by the patient
  "clinician" — message sent by a clinician (or care coordinator)

No attachment support in Slice 2 — plain text only.
"""

from __future__ import annotations

import datetime

from sqlalchemy import Index
from sqlmodel import Field, SQLModel


def _utcnow() -> datetime.datetime:
    """Return current UTC time as timezone-naive datetime (CLAUDE.md pattern)."""
    return datetime.datetime.now(datetime.UTC).replace(tzinfo=None)


class Message(SQLModel, table=True):
    """A single message in the patient ↔ care-team thread."""

    __tablename__ = "message"

    # Named index on patient_id — do NOT add index=True to Field below.
    __table_args__ = (Index("ix_message_patient_id", "patient_id"),)

    id: int | None = Field(default=None, primary_key=True)

    # Patient isolation boundary — indexed via __table_args__
    patient_id: str = Field(foreign_key="patient.patient_id")

    # "patient" | "clinician"
    sender: str

    # Plain-text message body
    content: str

    # When the message was sent (naive UTC)
    created_at: datetime.datetime = Field(default_factory=_utcnow)
