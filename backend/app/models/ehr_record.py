"""SQLModel entity: EHRRecord.

A single typed clinical record linked to a patient. The CSV adapter explodes
each source row into multiple EHRRecord rows (one per condition, one per
medication, one per visit, one lab_panel per patient).

Payload structure by record_type:
  - condition:   {"icd_code": str, "description": str}
  - medication:  {"name": str, "dose": str | None}
  - visit:       {"date": str (ISO-8601)}
  - lab_panel:   {"total_cholesterol_mmol": float, "ldl_mmol": float,
                   "hdl_mmol": float, "triglycerides_mmol": float,
                   "hba1c_pct": float, "fasting_glucose_mmol": float,
                   "crp_mg_l": float, "egfr_ml_min": float,
                   "sbp_mmhg": float, "dbp_mmhg": float}

The embedding column is declared here (Vector(768)) but is not populated in
this slice — reserved for the RAG layer (future sprint).

Lab panel recorded_at assumption: we use the latest wearable date for that
patient as a proxy timestamp. The CSV does not supply an explicit lab date.
This assumption is documented here and in the CSV adapter.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pgvector.sqlalchemy import Vector  # type: ignore[import-untyped]
from sqlalchemy import Column, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

# Documented record type literals — stored as plain str in the DB column,
# expressed as Literal here for IDE support and documentation clarity.
EHRRecordType = Literal["condition", "medication", "visit", "lab_panel"]


class EHRRecord(SQLModel, table=True):
    """Single typed clinical record for a patient.

    One source row may expand to many EHRRecord rows (condition × N,
    medication × N, visit × N, lab_panel × 1).
    """

    __tablename__ = "ehr_record"

    # Named index on patient_id — most efficient path for per-patient queries.
    # Also declared via Field(index=True) below; this __table_args__ entry
    # provides the spec-required "ix_<table>_patient_id" name.
    __table_args__ = (Index("ix_ehr_record_patient_id", "patient_id"),)

    # Auto-incrementing surrogate key
    id: int | None = Field(default=None, primary_key=True)

    # patient_id is indexed for efficient per-patient lookups
    patient_id: str = Field(foreign_key="patient.patient_id", index=True)

    # Discriminator — one of the four supported types
    record_type: str  # values: EHRRecordType; str for DB portability

    recorded_at: datetime

    # Structured payload stored as JSONB for schema flexibility
    payload: dict[str, Any] = Field(sa_column=Column(JSONB, nullable=False))

    # Adapter name — "csv", "fhir", etc.
    source: str

    # pgvector embedding — nullable; populated by the RAG layer in a future slice
    embedding: list[float] | None = Field(
        default=None,
        sa_column=Column(Vector(768), nullable=True),
    )
