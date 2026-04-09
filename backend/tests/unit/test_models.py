"""Unit tests for SQLModel entities (T5).

Tests instantiation and index declarations for all five models.
No DB connection required — SQLModel table=True models can be instantiated
as plain Python objects.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from sqlalchemy import inspect as sa_inspect


def _utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


# ---------------------------------------------------------------------------
# test_models_instantiable_with_required_fields
# ---------------------------------------------------------------------------


def test_patient_instantiable_with_required_fields() -> None:
    """Patient must be constructable with its documented required fields."""
    from app.models import Patient

    p = Patient(
        patient_id="PT0001",
        name="Alice Müller",
        age=42,
        sex="F",
        country="DE",
        created_at=_utcnow(),
        updated_at=_utcnow(),
    )
    assert p.patient_id == "PT0001"
    assert p.name == "Alice Müller"
    assert p.age == 42
    assert p.sex == "F"
    assert p.country == "DE"
    # Optional fields default to None
    assert p.height_cm is None
    assert p.weight_kg is None
    assert p.bmi is None
    assert p.smoking_status is None
    assert p.alcohol_units_weekly is None


def test_patient_accepts_optional_fields() -> None:
    """Optional Patient fields accept non-None values."""
    from app.models import Patient

    p = Patient(
        patient_id="PT0002",
        name="Bob Schmidt",
        age=55,
        sex="M",
        country="DE",
        height_cm=180.0,
        weight_kg=85.0,
        bmi=26.2,
        smoking_status="never",
        alcohol_units_weekly=4.0,
        created_at=_utcnow(),
        updated_at=_utcnow(),
    )
    assert p.height_cm == 180.0
    assert p.smoking_status == "never"


def test_ehr_record_instantiable_with_required_fields() -> None:
    """EHRRecord must be constructable with required fields."""
    from app.models import EHRRecord

    r = EHRRecord(
        patient_id="PT0001",
        record_type="condition",
        recorded_at=_utcnow(),
        payload={"icd_code": "I10", "description": "Hypertension"},
        source="csv",
    )
    assert r.patient_id == "PT0001"
    assert r.record_type == "condition"
    assert r.payload == {"icd_code": "I10", "description": "Hypertension"}
    assert r.source == "csv"
    assert r.id is None  # auto-incremented PK not set yet
    assert r.embedding is None


def test_ehr_record_accepts_all_record_types() -> None:
    """All four record_type literals must be valid string values."""
    from app.models import EHRRecord

    for rtype in ("condition", "medication", "visit", "lab_panel"):
        r = EHRRecord(
            patient_id="PT0001",
            record_type=rtype,
            recorded_at=_utcnow(),
            payload={},
            source="csv",
        )
        assert r.record_type == rtype


def test_wearable_day_instantiable_with_required_fields() -> None:
    """WearableDay must be constructable with composite PK fields."""
    from app.models import WearableDay

    w = WearableDay(
        patient_id="PT0001",
        date=date(2024, 3, 15),
    )
    assert w.patient_id == "PT0001"
    assert w.date == date(2024, 3, 15)
    # All metric fields are optional
    assert w.resting_hr_bpm is None
    assert w.steps is None
    assert w.sleep_duration_hrs is None


def test_wearable_day_accepts_all_metric_fields() -> None:
    """WearableDay must accept all columns from wearable_telemetry_1.csv."""
    from app.models import WearableDay

    w = WearableDay(
        patient_id="PT0001",
        date=date(2024, 3, 15),
        resting_hr_bpm=62,
        hrv_rmssd_ms=45.3,
        steps=8200,
        active_minutes=38,
        sleep_duration_hrs=7.5,
        sleep_quality_score=78.0,
        deep_sleep_pct=22.0,
        spo2_avg_pct=97.0,
        calories_burned_kcal=2100,
    )
    assert w.resting_hr_bpm == 62
    assert w.hrv_rmssd_ms == 45.3
    assert w.steps == 8200
    assert w.active_minutes == 38
    assert w.sleep_duration_hrs == 7.5
    assert w.sleep_quality_score == 78.0
    assert w.deep_sleep_pct == 22.0
    assert w.spo2_avg_pct == 97.0
    assert w.calories_burned_kcal == 2100


def test_lifestyle_profile_instantiable_with_required_fields() -> None:
    """LifestyleProfile must be constructable with just patient_id and survey_date."""
    from app.models import LifestyleProfile

    lp = LifestyleProfile(
        patient_id="PT0001",
        survey_date=date(2024, 1, 10),
    )
    assert lp.patient_id == "PT0001"
    assert lp.survey_date == date(2024, 1, 10)
    # All optional fields default to None
    assert lp.diet_quality_score is None
    assert lp.stress_level is None


def test_lifestyle_profile_accepts_all_fields() -> None:
    """LifestyleProfile must accept all columns from lifestyle_survey.csv."""
    from app.models import LifestyleProfile

    lp = LifestyleProfile(
        patient_id="PT0001",
        survey_date=date(2024, 1, 10),
        smoking_status="never",
        alcohol_units_weekly=3.0,
        diet_quality_score=7,
        fruit_veg_servings_daily=4.5,
        meal_frequency_daily=3,
        exercise_sessions_weekly=4,
        sedentary_hrs_day=6.0,
        stress_level=4,
        sleep_satisfaction=7,
        mental_wellbeing_who5=72,
        self_rated_health=8,
        water_glasses_daily=8,
    )
    assert lp.diet_quality_score == 7
    assert lp.mental_wellbeing_who5 == 72


def test_vitality_snapshot_instantiable_with_required_fields() -> None:
    """VitalitySnapshot must be constructable with all required fields."""
    from app.models import VitalitySnapshot

    vs = VitalitySnapshot(
        patient_id="PT0001",
        computed_at=_utcnow(),
        score=72.5,
        subscores={"cardio": 80.0, "sleep": 65.0},
        risk_flags={"lipid": {"severity": "moderate"}},
    )
    assert vs.patient_id == "PT0001"
    assert vs.score == 72.5
    assert vs.subscores["cardio"] == 80.0
    assert vs.risk_flags["lipid"]["severity"] == "moderate"


# ---------------------------------------------------------------------------
# test_patient_id_indexed_on_child_tables
# ---------------------------------------------------------------------------


def _get_index_names(table: object) -> set[str]:
    """Return the set of index names defined on a SQLAlchemy Table object."""
    # table.__table__ for SQLModel table=True classes
    sa_table = getattr(table, "__table__", table)
    return {idx.name for idx in sa_table.indexes}


def test_patient_id_indexed_on_ehr_record() -> None:
    """EHRRecord must declare an index on patient_id."""
    from app.models import EHRRecord

    index_names = _get_index_names(EHRRecord)
    # Either a named index or a Field(index=True) SQLAlchemy auto-index
    assert any("patient_id" in name for name in index_names), (
        f"No patient_id index found on ehr_record. Indexes: {index_names}"
    )


def test_patient_id_indexed_on_wearable_day() -> None:
    """WearableDay must declare an index on patient_id."""
    from app.models import WearableDay

    index_names = _get_index_names(WearableDay)
    assert any("patient_id" in name for name in index_names), (
        f"No patient_id index found on wearable_day. Indexes: {index_names}"
    )


def test_patient_id_is_pk_on_lifestyle_profile() -> None:
    """LifestyleProfile uses patient_id as PK (no separate index needed)."""
    from app.models import LifestyleProfile

    sa_table = LifestyleProfile.__table__
    pk_cols = {col.name for col in sa_table.primary_key.columns}
    assert "patient_id" in pk_cols


def test_patient_id_is_pk_on_vitality_snapshot() -> None:
    """VitalitySnapshot uses patient_id as PK."""
    from app.models import VitalitySnapshot

    sa_table = VitalitySnapshot.__table__
    pk_cols = {col.name for col in sa_table.primary_key.columns}
    assert "patient_id" in pk_cols


def test_wearable_day_composite_pk() -> None:
    """WearableDay PK must be (patient_id, date)."""
    from app.models import WearableDay

    sa_table = WearableDay.__table__
    pk_cols = {col.name for col in sa_table.primary_key.columns}
    assert pk_cols == {"patient_id", "date"}


def test_ehr_record_payload_column_type() -> None:
    """EHRRecord.payload must be backed by a JSONB or JSON column type."""
    from app.models import EHRRecord
    from sqlalchemy.dialects.postgresql import JSONB
    from sqlalchemy import JSON

    col = EHRRecord.__table__.c["payload"]
    # Accept both JSONB (postgres) and JSON (fallback for SQLite in tests)
    assert isinstance(col.type, (JSONB, JSON)), (
        f"Expected JSONB/JSON column type, got: {type(col.type)}"
    )


def test_vitality_snapshot_subscores_column_type() -> None:
    """VitalitySnapshot.subscores must be JSONB or JSON."""
    from app.models import VitalitySnapshot
    from sqlalchemy.dialects.postgresql import JSONB
    from sqlalchemy import JSON

    col = VitalitySnapshot.__table__.c["subscores"]
    assert isinstance(col.type, (JSONB, JSON)), (
        f"Expected JSONB/JSON, got: {type(col.type)}"
    )


def test_models_init_exports_all_classes() -> None:
    """app.models.__init__ must export all five model classes."""
    from app.models import (
        Patient,
        EHRRecord,
        WearableDay,
        LifestyleProfile,
        VitalitySnapshot,
    )

    for cls in (Patient, EHRRecord, WearableDay, LifestyleProfile, VitalitySnapshot):
        assert cls is not None
        assert hasattr(cls, "__tablename__")
