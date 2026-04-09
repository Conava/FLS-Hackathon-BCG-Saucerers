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
    patient_id: str = Field(primary_key=True)  # e.g. "PT0001" from source system
    name: str
    age: int          # CSV datasets provide age, not date_of_birth
    sex: str
    country: str

    # Biometric — optional; absent rows allowed
    height_cm: float | None = None
    weight_kg: float | None = None
    bmi: float | None = None

    # Lifestyle summary copied from EHR CSV row for quick access
    # (LifestyleProfile holds the full per-survey breakdown)
    smoking_status: str | None = None
    alcohol_units_weekly: float | None = None

    created_at: datetime  # naive UTC — see CLAUDE.md Lessons
    updated_at: datetime

class EHRRecord(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    patient_id: str = Field(foreign_key="patient.patient_id")
    recorded_at: datetime
    record_type: str          # "diagnosis", "medication", "visit", "lab"
    content: str              # human-readable summary (RAG-indexed via pgvector)
    structured: dict          # JSON — codes, values, units
    embedding: list[float] | None = Field(sa_column=Column(Vector(768)))  # populated at ingest via LLMProvider.embed
    source: str               # adapter name: "csv", "fhir", ...

class WearableDay(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    patient_id: str = Field(foreign_key="patient.patient_id")
    date: date
    resting_hr: float | None
    steps: int | None
    sleep_hours: float | None
    sleep_quality: float | None
    # ... etc.

class LifestyleProfile(SQLModel, table=True):
    """Typed projection of the onboarding survey. One row per patient, overwritten on retake."""
    patient_id: str = Field(foreign_key="patient.patient_id", primary_key=True)
    # goals & motivation
    primary_goal: str | None
    motivation_type: str | None
    # sleep
    sleep_hours_typical: float | None
    sleep_quality_self: int | None        # 1–5
    # activity
    exercise_sessions_per_week: int | None
    exercise_intensity: str | None        # light | moderate | vigorous
    # nutrition
    diet_pattern: str | None              # omnivore | vegetarian | vegan | low_carb | mediterranean | other
    meals_per_day: int | None
    ultra_processed_frequency: str | None
    cooking_willingness: int | None       # 1–5
    dietary_restrictions: list[str] | None = Field(sa_column=Column(JSON))
    known_allergies: list[str] | None = Field(sa_column=Column(JSON))
    alcohol_units_per_week: float | None
    caffeine_cups_per_day: float | None
    # mind & social
    stress_level: int | None              # 1–5
    social_connection: int | None         # 1–5
    # constraints & commerce gating
    time_budget_minutes_per_day: int | None
    out_of_pocket_budget_eur_per_month: float | None
    injuries_or_limitations: list[str] | None = Field(sa_column=Column(JSON))
    data_sources_consented: list[str] | None = Field(sa_column=Column(JSON))
    last_full_retake_at: datetime | None
    last_micro_survey_at: datetime | None

class VitalitySnapshot(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    patient_id: str = Field(foreign_key="patient.patient_id")
    computed_at: datetime
    score: float                          # 0–100 composite
    sub_scores: dict                      # one per longevity dimension
    flags: list[str]                      # wellness-framed risk flags
```

**Slice-2 models** (shipped in slice 2): `SurveyResponse`, `Protocol`, `ProtocolAction`, `DailyLog`, `MealLog`, `VitalityOutlook`, `Message`, `Notification`, `ClinicalReview`, `Referral`. All tables are created at startup via `db.base.create_all`, which also ensures the `vector` extension and HNSW index are present.

**Manual-tracker columns** (added as nullable, backwards-compatible): `DailyLog` gained `sleep_quality: int | None` (1–5), `workout_type: str | None` (`walk|run|bike|strength|yoga|other`), and `workout_intensity: str | None` (`low|med|high`). `ProtocolAction` gained `sort_order: int | None` (explicit display order, `NULLS LAST` in list query), `skipped_today: bool` (default `false`), and `skip_reason: str | None`. Manual meal entries use the existing `MealLog` table with `photo_uri = "manual://<uuid>"` as a sentinel value — readers check for the `manual://` prefix before rendering a photo.

### Design principles

1. **Source-agnostic downstream.** The score engine and AI layer never ask *where* data came from — only what it is.
2. **Patient ID is the hard isolation boundary.** Every query filters by `patient_id`. No exceptions. This is a security invariant, not a convention.
3. **Embeddings live next to content.** One `EHRRecord` row = text + structured + vector. Simpler than a separate vector table.
4. **Structured + unstructured together.** Keep `content` (text for RAG) and `structured` (codes/values for scoring) on the same record.
5. **Immutable history.** Snapshots are append-only. Deletion only via consent revocation flow.

## CSV adapter implementation (shipped in slice 1)

The `CSVDataSource` adapter (`app/adapters/csv_source.py`) loads the three provided datasets into the unified schema. Each CSV row is **exploded** into multiple model instances: one `Patient` + one `LifestyleProfile` + N `EHRRecord` rows (one per distinct diagnosis/medication/visit coded in the row) + M `WearableDay` rows (one per calendar day in the telemetry window).

- `ehr_records.csv` → `Patient` + `LifestyleProfile` + `EHRRecord` rows per patient
- `wearable_telemetry_1.csv` → `WearableDay` rows (up to 90 days per patient)

`lifestyle_survey.csv` fields are merged into `LifestyleProfile` at ingest time. Survey-only fields not present in the CSVs (`diet_pattern`, `time_budget_minutes_per_day`, `out_of_pocket_budget_eur_per_month`, etc.) are left null and filled when the user completes the in-app onboarding survey.

The adapter yields one `PatientData` bundle per patient via an `async` generator, keeping memory bounded across 1,000+ patients.

Embedding generation uses `FakeLLMProvider` (dev/CI) or `GeminiProvider` (`text-embedding-004` via Vertex AI) depending on `LLM_PROVIDER`. Embeddings are populated during ingest — every `EHRRecord.embedding` column is non-null after `make seed`. An HNSW index (`vector_cosine_ops`) is created automatically at startup.

Run the ingest:

```bash
# Via docker-compose (recommended)
make seed

# Directly (from backend/)
uv run python -m app.cli.ingest --source=csv --data-dir=../data
```

## Vitality Score engine — aligned to the brief's four dimensions

The composite score patients see every day. Sub-scores map 1:1 to the four "exemplary" longevity dimensions from the BCG brief — this alignment is deliberate pitch ammunition.

```
Vitality Score (0–100)
├── Biological Age (0–100)            heuristic from sleep, HRV proxy, VO2max proxy, ApoB, HbA1c
├── Sleep & Recovery (0–100)          from wearable: duration, quality, HRV proxy
├── Cardiovascular Fitness (0–100)    from wearable + EHR: resting HR, BP, VO2max proxy, lipid panel
└── Lifestyle & Behavioral Risk       from survey: diet pattern, alcohol, stress, activity, social
    (0–100)
```

Weights are v1 heuristic — document as "clinically-informed, not clinically-validated" in the pitch. V2 story: *"we retrain weights on outcomes from the 10M-patient cohort."*

### Vitality Outlook (near-term projection)

Distinct from the raw Score. Drives the forward-looking curve on Today.

```
Outlook(h months) = Score_now + Σ (streak_weight[category] × streak_days × decay(h))
```

- **Streak weight** per action category is a heuristic (nutrition = 0.15/day capped, sleep = 0.20, movement = 0.15, mind = 0.10, supplement = 0.05).
- **Decay** tempers the projection so 12-month outlook isn't unboundedly optimistic.
- **Breaking a streak flattens the curve — never drops the current Score.** This is a product choice, not a technical one: punitive scoring kills retention.
- Computed on login and on any protocol-completion event. Cached in `VitalityOutlook`.

### Long-horizon Future-self simulator

Stateless — not persisted. A Gemini call that takes lifestyle sliders (sleep, activity, nutrition, alcohol) and returns a projected biological age + score at 70, current path vs. improved path. Lives in Insights next to the near-term Outlook. See [06-ai-layer.md](06-ai-layer.md) for the prompt contract.

## Open questions

- Should `VitalitySnapshot.sub_scores` be a typed SQLModel or a JSON dict? Leaning JSON for demo speed.
- Do we compute vitality on every request or cache daily snapshots? Leaning: cache, recompute on demand.
- How do we handle patients with missing wearable data? (Likely most of the 1,000 CSV patients.) Fallback: score what we have, flag the gap, nudge to connect a wearable.
