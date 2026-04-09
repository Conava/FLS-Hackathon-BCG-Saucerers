"""EHR record response DTOs.

Defines schemas for individual EHR records and paginated list responses.
``payload`` is a free-form dict — its shape varies by ``record_type``:
  - ``lab_panel``: ``{total_cholesterol_mmol, ldl_mmol, hdl_mmol, ...}``
  - ``condition``:  ``{name, icd10, ...}``
  - ``medication``: ``{name, dose, frequency, ...}``
  - ``visit``:      ``{date, provider, notes, ...}``
"""

from __future__ import annotations

import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class EHRRecordOut(BaseModel):
    """Response schema for a single EHR record."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Auto-incremented record PK")
    record_type: str = Field(
        ...,
        description="Record category: condition | medication | visit | lab_panel",
    )
    recorded_at: datetime.datetime = Field(..., description="When this record was created/measured")
    payload: dict[str, Any] = Field(..., description="Record-type-specific structured payload")
    source: str = Field(..., description="Adapter that produced this record, e.g. 'csv'")


class EHRRecordListOut(BaseModel):
    """Paginated list of EHR records for a patient."""

    model_config = ConfigDict(from_attributes=True)

    patient_id: str = Field(..., description="Patient the records belong to")
    records: list[EHRRecordOut] = Field(default_factory=list)
    total: int = Field(..., description="Total number of records (unpaged count)")
