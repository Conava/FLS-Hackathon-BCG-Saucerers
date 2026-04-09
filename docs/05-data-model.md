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
    """Typed projection of the onboarding survey. One row per patient, overwritten on retake.
    Free-text answers are *also* stored as SurveyResponse rows with embeddings for RAG."""
    patient_id: str = Field(foreign_key="patient.id", primary_key=True)
    # goals & motivation
    primary_goal: str | None              # live_longer | feel_better | manage_condition | performance
    motivation_type: str | None           # aesthetics | performance | disease_avoidance | longevity_curious
    # sleep
    sleep_hours_typical: float | None
    sleep_quality_self: int | None        # 1–5
    # activity
    exercise_sessions_per_week: int | None
    exercise_intensity: str | None        # light | moderate | vigorous
    # nutrition (new — first-class)
    diet_pattern: str | None              # omnivore | vegetarian | vegan | low_carb | mediterranean | other
    meals_per_day: int | None
    ultra_processed_frequency: str | None # rarely | sometimes | daily | every_meal
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

class SurveyResponse(SQLModel, table=True):
    """Append-only record of every survey answer (onboarding, weekly micro, quarterly).
    Stored as free-text + embedding so Coach can retrieve nuanced self-reports via RAG."""
    id: int | None = Field(default=None, primary_key=True)
    patient_id: str = Field(foreign_key="patient.id", index=True)
    taken_at: datetime
    survey_kind: str                      # onboarding | weekly_micro | quarterly_deep
    question_key: str                     # stable identifier of the question asked
    answer_text: str                      # what the user wrote or the label they picked
    answer_structured: dict | None = Field(sa_column=Column(JSON))  # numeric/enum mirror when applicable
    embedding: list[float] | None = Field(sa_column=Column(Vector(768)))

class Protocol(SQLModel, table=True):
    """A weekly set of daily actions generated by Coach. One active protocol per patient at a time."""
    id: int | None = Field(default=None, primary_key=True)
    patient_id: str = Field(foreign_key="patient.id", index=True)
    generated_at: datetime
    generated_by: str                     # "coach_auto" | "user_edit" | "coach_nudge"
    week_starts_on: date
    rationale: str                        # one-paragraph summary Coach shows the user
    is_active: bool = True

class ProtocolAction(SQLModel, table=True):
    """One daily action inside a Protocol. Streak state lives on the DailyLog rows, not here."""
    id: int | None = Field(default=None, primary_key=True)
    protocol_id: int = Field(foreign_key="protocol.id", index=True)
    patient_id: str = Field(foreign_key="patient.id", index=True)
    category: str                         # movement | sleep | nutrition | mind | supplement
    title: str                            # "25-min walk"
    target: str                           # "25 minutes" | "lights out by 22:30" | "swap rice for lentils"
    rationale: str                        # one-line, links to Coach explanation
    dimension: str                        # biological_age | sleep_recovery | cardio_fitness | lifestyle_behavioral

class DailyLog(SQLModel, table=True):
    """Self-tracking + protocol completion. One row per (patient, date, entry)."""
    id: int | None = Field(default=None, primary_key=True)
    patient_id: str = Field(foreign_key="patient.id", index=True)
    logged_at: datetime
    log_date: date                        # the day the entry is *about* (may differ from logged_at)
    entry_type: str                       # protocol_complete | meal | mood | workout | sleep | water | alcohol
    protocol_action_id: int | None = Field(default=None, foreign_key="protocolaction.id")
    structured: dict | None = Field(sa_column=Column(JSON))  # macros, duration, intensity, rating, etc.
    note: str | None                      # free-text

class MealLog(SQLModel, table=True):
    """Photo-driven meal log. Nutrition is woven-in, not a separate tab."""
    id: int | None = Field(default=None, primary_key=True)
    patient_id: str = Field(foreign_key="patient.id", index=True)
    taken_at: datetime
    image_uri: str | None                 # Cloud Storage path (optional)
    classification: str                   # what Gemini vision said this is
    macros: dict = Field(sa_column=Column(JSON))  # kcal, protein_g, carbs_g, fat_g, fiber_g, polyphenols_flag
    longevity_swap: str | None            # one-line swap suggestion Coach generated
    swap_accepted: bool | None

class VitalitySnapshot(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    patient_id: str = Field(foreign_key="patient.id", index=True)
    computed_at: datetime
    score: float                          # 0–100 composite — slow-moving, biomarker + wearable driven
    sub_scores: dict                      # one per longevity dimension (see score engine below)
    flags: list[str]                      # risk flags surfaced, each tagged with a dimension

class VitalityOutlook(SQLModel, table=True):
    """Near-term forward projection driven by streak momentum on the active protocol.
    Distinct from the long-horizon Future-self simulator (which is a stateless Gemini call)."""
    id: int | None = Field(default=None, primary_key=True)
    patient_id: str = Field(foreign_key="patient.id", index=True)
    computed_at: datetime
    horizon_months: int                   # 3 | 6 | 12
    projected_score: float                # where the score is trending if streak holds
    streak_days: int                      # current overall streak at time of computation
    drivers: dict                         # {action_category: weight_contribution}
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
- `lifestyle_survey.csv` → `LifestyleProfile` rows (mapped to the subset of fields the CSV covers; new survey fields like `diet_pattern`, `alcohol_units_per_week`, `time_budget_minutes_per_day`, `out_of_pocket_budget_eur_per_month` are left null and filled on first in-app survey)

During load:
1. Parse + validate each row
2. Generate `content` text for EHR records ("Diagnosed with hypertension on 2024-03-15, prescribed losartan 50mg")
3. Embed `content` via `text-embedding-004` in batches
4. Insert via SQLModel bulk insert

This runs once at startup or via a CLI command `uv run python -m app.scripts.load_csv`.

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
