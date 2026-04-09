"""Referral request/response DTOs.

``ReferralIn`` is the inbound payload for creating a specialist referral.
``ReferralOut`` is the response for a persisted referral row.

These are stubs — the MVP persists the row but does not route to a real
booking or specialist coordination system.

Wellness framing: ``reason`` should use wellness language rather than
diagnostic verbs. The API consumer is responsible for compliance.
"""

from __future__ import annotations

import datetime

from pydantic import BaseModel, ConfigDict, Field


class ReferralIn(BaseModel):
    """Inbound payload for ``POST /v1/patients/{pid}/referral``."""

    model_config = ConfigDict(from_attributes=True)

    patient_id: str = Field(..., description="Patient the referral is for")
    specialty: str = Field(
        ...,
        description="Medical specialty for the referral, e.g. 'cardiology', 'dermatology'",
    )
    reason: str = Field(
        ...,
        description="Wellness-framed reason for the referral",
    )


class ReferralOut(BaseModel):
    """API response schema for a persisted referral row."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Referral primary key")
    patient_id: str = Field(..., description="Patient the referral belongs to")
    specialty: str = Field(..., description="Target medical specialty")
    reason: str = Field(..., description="Referral reason")
    status: str = Field(
        ...,
        description="Referral status: 'pending' | 'sent' | 'completed'",
    )
    created_at: datetime.datetime = Field(
        ...,
        description="Timestamp when the referral was created (naive UTC)",
    )
