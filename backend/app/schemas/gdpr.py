"""GDPR compliance response DTOs.

``GDPRExportOut`` bundles all data held for a patient — a right-of-access
response under GDPR Art. 15.

``GDPRDeleteAck`` is the right-to-erasure acknowledgement under GDPR Art. 17.
Actual deletion is a stub in this slice (documented in T14) — the status is
always ``"scheduled"`` and the message is wellness-framed to avoid any
implication that medical records have been permanently destroyed without
proper archival review.

Fields use ``Any`` for the bundle's sub-structures so this DTO does not
import SQLModel entities (DTOs are independent of table models per T6 spec).
"""

from __future__ import annotations

import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.patient import PatientProfileOut
from app.schemas.records import EHRRecordOut
from app.schemas.wearable import WearableDayOut


class GDPRExportOut(BaseModel):
    """Bundled personal data export for a patient (GDPR Art. 15 response)."""

    model_config = ConfigDict(from_attributes=True)

    patient_id: str = Field(..., description="Patient identifier")
    patient: PatientProfileOut = Field(..., description="Demographic profile")
    records: list[EHRRecordOut] = Field(
        default_factory=list,
        description="All EHR records held for this patient",
    )
    wearable: list[WearableDayOut] = Field(
        default_factory=list,
        description="All wearable telemetry held for this patient",
    )
    lifestyle: Any = Field(
        None,
        description="Lifestyle survey data (structure varies by adapter)",
    )
    exported_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.UTC).replace(tzinfo=None),
        description="Timestamp of this export (naive UTC, matches DB columns)",
    )


class GDPRDeleteAck(BaseModel):
    """Acknowledgement of a data-erasure request (GDPR Art. 17).

    ``status`` is always ``"scheduled"`` — deletion is asynchronous and
    subject to legal retention obligations. The message is wellness-framed.
    """

    model_config = ConfigDict(from_attributes=True)

    status: Literal["scheduled"] = Field(
        "scheduled",
        description="Erasure request status — always 'scheduled' in this slice",
    )
    message: str = Field(
        ...,
        description="Human-readable acknowledgement (wellness-framed)",
    )
