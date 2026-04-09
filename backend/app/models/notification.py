"""SQLModel entity: Notification.

In-app notification record. Each row represents a notification pushed to the
patient's device (or displayed as an in-app banner). Delivery is handled by the
notifications service; this table is the audit trail.

The ``kind`` field categorises the notification type for UI rendering:
  "nudge"            — daily protocol reminder
  "insight"          — AI-surfaced risk flag or opportunity
  "commerce"         — contextual offer (diagnostic panel, supplement)
  "clinical_review"  — clinician has reviewed a flag
  "message"          — new care-team message
  "survey_prompt"    — time for weekly/quarterly survey

``cta`` is an optional call-to-action deep-link (e.g. "/today/protocol/3").
``delivered_at`` / ``read_at`` are nullable — null means not yet delivered/read.
"""

from __future__ import annotations

import datetime

from sqlalchemy import Index
from sqlmodel import Field, SQLModel


def _utcnow() -> datetime.datetime:
    """Return current UTC time as timezone-naive datetime (CLAUDE.md pattern)."""
    return datetime.datetime.now(datetime.UTC).replace(tzinfo=None)


class Notification(SQLModel, table=True):
    """A single in-app notification for a patient."""

    __tablename__ = "notification"

    # Named index on patient_id — do NOT add index=True to Field below.
    __table_args__ = (Index("ix_notification_patient_id", "patient_id"),)

    id: int | None = Field(default=None, primary_key=True)

    # Patient isolation boundary — indexed via __table_args__
    patient_id: str = Field(foreign_key="patient.patient_id")

    # Notification category (see module docstring for valid values)
    kind: str

    # Short notification headline
    title: str

    # Notification body text
    body: str

    # Optional deep-link URI (e.g. "/today/protocol/3")
    cta: str | None = Field(default=None)

    # Delivery and read timestamps — null until the events occur (naive UTC)
    delivered_at: datetime.datetime | None = Field(default=None)
    read_at: datetime.datetime | None = Field(default=None)

    # When this row was created (naive UTC)
    created_at: datetime.datetime = Field(default_factory=_utcnow)
