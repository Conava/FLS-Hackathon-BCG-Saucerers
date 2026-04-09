"""SQLModel entity: Referral.

Represents a patient referral record. Used for the referral program (journey
stage 10 from the persona doc — "refer a friend").

``code`` is the unique shareable referral code (generated at creation time).
``referred_patient_id`` is populated when the referred person signs up and is
linked via their patient ID. Nullable until redemption.

Status lifecycle:
  "pending"   — code generated; not yet redeemed
  "redeemed"  — referred person has signed up and been linked
  "expired"   — code expired without redemption
"""

from __future__ import annotations

import datetime

from sqlalchemy import Index
from sqlmodel import Field, SQLModel


def _utcnow() -> datetime.datetime:
    """Return current UTC time as timezone-naive datetime (CLAUDE.md pattern)."""
    return datetime.datetime.now(datetime.UTC).replace(tzinfo=None)


class Referral(SQLModel, table=True):
    """A referral record linking a referring patient to a new patient."""

    __tablename__ = "referral"

    # Named index on patient_id — do NOT add index=True to Field below.
    __table_args__ = (Index("ix_referral_patient_id", "patient_id"),)

    id: int | None = Field(default=None, primary_key=True)

    # Referring patient — isolation boundary; indexed via __table_args__
    patient_id: str = Field(foreign_key="patient.patient_id")

    # Unique shareable referral code (e.g. "REF-ABCD-1234")
    code: str

    # FK to the new patient once they sign up (nullable until redemption)
    referred_patient_id: str | None = Field(default=None)

    # Status: "pending" | "redeemed" | "expired"
    status: str

    # When this referral was created (naive UTC)
    created_at: datetime.datetime = Field(default_factory=_utcnow)
