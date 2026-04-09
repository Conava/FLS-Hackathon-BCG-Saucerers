# 05 — Data Model & Adapter Layer

The client's #1 structural barrier (per the brief) is **fragmented data**. The core architectural move of this MVP is a **pluggable data adapter layer** that fuses every source into a single **Unified Patient Profile**.

For system-level diagrams see [03-architecture.md](03-architecture.md). For version pins see [04-tech-stack.md](04-tech-stack.md).

## Pluggable adapter pattern

One protocol, many implementations. Today we have CSVs. Tomorrow we plug in FHIR, Apple Health, Doctolib, lab APIs — in <50 lines each.

```python
from typing import Protocol
from app.models import PatientData

class DataSource(Protocol):
    name: str                                    # "csv", "fhir", "apple-health", ...
    def fetch_patient(self, patient_id: str) -> PatientData: ...
    def supports(self, capability: str) -> bool: ...   # e.g. "ehr", "wearable", "lifestyle"
```

Concrete implementations:
```python
class CSVDataSource:      # today — loads the 3 provided CSVs
class FHIRDataSource:     # v2 — standard EHR protocol
class AppleHealthDataSource:  # v2
class DoctolibDataSource: # v2 — appointments
class LabProviderSource:  # v2 — blood panels
```

The **Unified Patient Profile service** orchestrates all registered sources, merges results, and hands a single `PatientData` object to every downstream consumer (score engine, AI coach, RAG indexer).

**Pitch line:** *"Adding a new data source is under 50 lines of code. The unified profile, the scoring engine, and the AI coach don't change when we plug in Apple Health or Doctolib next sprint."*

## Unified Patient Profile — the canonical shape

This is the shape every AI call, every score, every UI screen reads from. One schema to rule them all.

```python
from sqlmodel import SQLModel, Field, Relationship
from datetime import date, datetime
from pgvector.sqlalchemy import Vector

class Patient(SQLModel, table=True):
    id: str = Field(primary_key=True)
    name: str
    date_of_birth: date
    sex: str
    # ... + consent flags, clinic_id, etc.

    ehr_records: list["EHRRecord"] = Relationship(back_populates="patient")
    wearable_days: list["WearableDay"] = Relationship(back_populates="patient")
    lifestyle: "LifestyleProfile" = Relationship(back_populates="patient")
    vitality_snapshots: list["VitalitySnapshot"] = Relationship(back_populates="patient")

class EHRRecord(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    patient_id: str = Field(foreign_key="patient.id", index=True)
    recorded_at: datetime
    record_type: str          # "diagnosis", "medication", "visit", "lab"
    content: str              # human-readable summary for RAG
    structured: dict          # JSON — codes, values, units
    embedding: list[float] | None = Field(sa_column=Column(Vector(768)))
    source: str               # adapter name: "csv", "fhir", ...

class WearableDay(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    patient_id: str = Field(foreign_key="patient.id", index=True)
    date: date
    resting_hr: float | None
    steps: int | None
    sleep_hours: float | None
    sleep_quality: float | None
    # ... etc.

class LifestyleProfile(SQLModel, table=True):
    patient_id: str = Field(foreign_key="patient.id", primary_key=True)
    diet_quality: int | None         # 1–10 self-reported
    exercise_frequency: int | None   # sessions/week
    stress_level: int | None         # 1–10
    # ... etc.

class VitalitySnapshot(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    patient_id: str = Field(foreign_key="patient.id", index=True)
    computed_at: datetime
    score: float                      # 0–100 composite
    sub_scores: dict                  # {sleep, recovery, activity, metabolic, cardio}
    flags: list[str]                  # risk flags surfaced
```

### Design principles

1. **Source-agnostic downstream.** The score engine and AI layer never ask *where* data came from — only what it is.
2. **Patient ID is the hard isolation boundary.** Every query filters by `patient_id`. No exceptions. This is a security invariant, not a convention.
3. **Embeddings live next to content.** One `EHRRecord` row = text + structured + vector. Simpler than a separate vector table.
4. **Structured + unstructured together.** Keep `content` (text for RAG) and `structured` (codes/values for scoring) on the same record.
5. **Immutable history.** Snapshots are append-only. Deletion only via consent revocation flow.

## CSV adapter implementation (hour-1 deliverable)

Loads the 3 provided datasets into the unified schema:
- `ehr_records.csv` → `EHRRecord` rows (1,000 patients)
- `wearable_telemetry_1.csv` → `WearableDay` rows (90-day history per patient)
- `lifestyle_survey.csv` → `LifestyleProfile` rows

During load:
1. Parse + validate each row
2. Generate `content` text for EHR records ("Diagnosed with hypertension on 2024-03-15, prescribed losartan 50mg")
3. Embed `content` via `text-embedding-004` in batches
4. Insert via SQLModel bulk insert

This runs once at startup or via a CLI command `uv run python -m app.scripts.load_csv`.

## Vitality Score engine

The composite score patients see every day.

```
Vitality Score (0–100)
├── Sleep & Recovery (0–100)   from wearable: duration, quality, HRV proxy
├── Activity (0–100)           from wearable: steps, active minutes
├── Metabolic (0–100)          from EHR labs: glucose, HbA1c, ApoB trendlines
├── Cardiovascular (0–100)     from EHR + wearable: resting HR, BP, family hx
└── Lifestyle (0–100)          from survey: diet, stress, exercise frequency
```

Weights are v1 heuristic — document as "clinically-informed, not clinically-validated" in the pitch. V2 story: "we retrain weights on outcomes from the 10M-patient cohort."

## Open questions

- Should `VitalitySnapshot.sub_scores` be a typed SQLModel or a JSON dict? Leaning JSON for demo speed.
- Do we compute vitality on every request or cache daily snapshots? Leaning: cache, recompute on demand.
- How do we handle patients with missing wearable data? (Likely most of the 1,000 CSV patients.) Fallback: score what we have, flag the gap, nudge to connect a wearable.
