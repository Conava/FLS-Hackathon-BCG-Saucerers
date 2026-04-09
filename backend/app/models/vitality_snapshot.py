"""SQLModel entity: VitalitySnapshot.

One row per patient — the most recent computed vitality score. This is an
upsert target: insert on first compute, update on subsequent computes.

The heuristic vitality engine (app.services.vitality_engine) computes the
score from the patient's unified profile; it is opportunistically persisted
here after each computation (write-through cache semantics).

Subscores structure (documented contract for the vitality engine):
  {"cardio": float, "metabolic": float, "sleep": float,
   "activity": float, "lifestyle": float}

risk_flags structure (wellness-framed — no diagnostic language):
  {"<signal_key>": {"severity": "low|moderate|high", "label": str, ...}}
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


class VitalitySnapshot(SQLModel, table=True):
    """Latest computed vitality score for a patient (single-row per patient)."""

    __tablename__ = "vitality_snapshot"

    # patient_id is both PK and FK — enforces one-row-per-patient and provides
    # the isolation boundary. No separate index needed (PK index covers queries).
    patient_id: str = Field(foreign_key="patient.patient_id", primary_key=True)

    computed_at: datetime

    # Composite score 0–100 (heuristic, not clinically validated)
    score: float

    # Dimension breakdown — JSONB for schema evolution without migrations
    subscores: dict[str, Any] = Field(sa_column=Column(JSONB, nullable=False))

    # Wellness signals — wellness-framed (never "diagnosis" / "treatment")
    risk_flags: dict[str, Any] = Field(sa_column=Column(JSONB, nullable=False))
