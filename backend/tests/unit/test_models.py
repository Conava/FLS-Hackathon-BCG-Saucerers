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


def test_no_duplicate_patient_id_indexes_on_ehr_record() -> None:
    """EHRRecord must declare patient_id in exactly one index (not two).

    Regression test for the duplicate index bug: Field(index=True) combined
    with __table_args__ Index(...) causes Postgres to fail with
    'relation already exists' at create_all() time.
    """
    from app.models import EHRRecord

    count = sum(
        1
        for idx in EHRRecord.__table__.indexes
        if any(c.name == "patient_id" for c in idx.columns)
    )
    assert count == 1, (
        f"EHRRecord has {count} indexes on patient_id (expected exactly 1). "
        "Remove index=True from Field(...) and keep only __table_args__ Index."
    )


def test_no_duplicate_patient_id_indexes_on_wearable_day() -> None:
    """WearableDay must declare patient_id in exactly one index (not two).

    Regression test for the duplicate index bug: same as EHRRecord.
    WearableDay.patient_id is also the PK, so the named __table_args__ index
    is the only explicit index that should appear.
    """
    from app.models import WearableDay

    count = sum(
        1
        for idx in WearableDay.__table__.indexes
        if any(c.name == "patient_id" for c in idx.columns)
    )
    assert count == 1, (
        f"WearableDay has {count} indexes on patient_id (expected exactly 1). "
        "Remove index=True from Field(...) and keep only __table_args__ Index."
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


# ---------------------------------------------------------------------------
# Slice 2 model tests (T2)
# ---------------------------------------------------------------------------


def test_models_init_exports_slice2_classes() -> None:
    """app.models.__init__ must export all Slice 2 model classes."""
    from app.models import (
        Protocol,
        ProtocolAction,
        DailyLog,
        MealLog,
        SurveyResponse,
        VitalityOutlook,
        Message,
        Notification,
        ClinicalReview,
        Referral,
    )

    for cls in (
        Protocol,
        ProtocolAction,
        DailyLog,
        MealLog,
        SurveyResponse,
        VitalityOutlook,
        Message,
        Notification,
        ClinicalReview,
        Referral,
    ):
        assert cls is not None
        assert hasattr(cls, "__tablename__")


# --- Protocol ---

def test_protocol_instantiable_with_required_fields() -> None:
    """Protocol must be constructable with its required fields."""
    from app.models import Protocol

    p = Protocol(
        patient_id="PT0001",
        week_start=date(2026, 4, 7),
        status="active",
    )
    assert p.patient_id == "PT0001"
    assert p.week_start == date(2026, 4, 7)
    assert p.status == "active"
    assert p.id is None


def test_protocol_created_at_is_naive_utc() -> None:
    """Protocol.created_at default must be timezone-naive."""
    from app.models import Protocol

    p = Protocol(patient_id="PT0001", week_start=date(2026, 4, 7), status="active")
    assert p.created_at.tzinfo is None


def test_protocol_round_trip_model_dump() -> None:
    """Protocol model_dump must round-trip through model_validate."""
    from app.models import Protocol

    p = Protocol(
        patient_id="PT0001",
        week_start=date(2026, 4, 7),
        status="active",
        generated_by="gemini-2.5-flash",
    )
    data = p.model_dump()
    p2 = Protocol.model_validate(data)
    assert p2.patient_id == p.patient_id
    assert p2.generated_by == "gemini-2.5-flash"


def test_protocol_action_instantiable() -> None:
    """ProtocolAction must be constructable with all required fields."""
    from app.models import ProtocolAction

    a = ProtocolAction(
        protocol_id=1,
        category="movement",
        title="Walk 25 minutes",
        rationale="Low-impact cardio supports heart health.",
        target_value="25 min",
        streak_days=3,
    )
    assert a.protocol_id == 1
    assert a.category == "movement"
    assert a.streak_days == 3
    assert a.id is None


def test_protocol_action_defaults() -> None:
    """ProtocolAction streak_days should default to 0."""
    from app.models import ProtocolAction

    a = ProtocolAction(
        protocol_id=1,
        category="sleep",
        title="Lights out by 22:30",
        rationale="Consistent sleep onset improves HRV.",
    )
    assert a.streak_days == 0
    assert a.completed_today is False


# --- DailyLog ---

def test_daily_log_instantiable_with_required_fields() -> None:
    """DailyLog must be constructable with just patient_id and logged_at."""
    from app.models import DailyLog

    dl = DailyLog(patient_id="PT0001", logged_at=datetime(2026, 4, 9, 8, 0, 0))
    assert dl.patient_id == "PT0001"
    assert dl.id is None
    # All optional metric fields default to None
    assert dl.mood is None
    assert dl.workout_minutes is None
    assert dl.sleep_hours is None
    assert dl.water_ml is None
    assert dl.alcohol_units is None
    assert dl.protocol_action_id is None


def test_daily_log_logged_at_naive() -> None:
    """DailyLog.logged_at must store as naive datetime."""
    from app.models import DailyLog

    dl = DailyLog(patient_id="PT0001", logged_at=datetime(2026, 4, 9, 8, 0, 0))
    assert dl.logged_at.tzinfo is None


def test_daily_log_patient_id_indexed() -> None:
    """DailyLog must declare an index on patient_id."""
    from app.models import DailyLog

    index_names = _get_index_names(DailyLog)
    assert any("patient_id" in n for n in index_names), (
        f"No patient_id index on daily_log. Indexes: {index_names}"
    )


def test_daily_log_no_duplicate_patient_id_indexes() -> None:
    """DailyLog must have exactly one index covering patient_id."""
    from app.models import DailyLog

    count = sum(
        1
        for idx in DailyLog.__table__.indexes
        if any(c.name == "patient_id" for c in idx.columns)
    )
    assert count == 1, f"DailyLog has {count} patient_id indexes (expected 1)"


# --- MealLog ---

def test_meal_log_instantiable_with_required_fields() -> None:
    """MealLog must be constructable with required fields."""
    from app.models import MealLog

    ml = MealLog(
        patient_id="PT0001",
        photo_uri="local://var/photos/PT0001/abc123.jpg",
        analyzed_at=datetime(2026, 4, 9, 12, 0, 0),
    )
    assert ml.patient_id == "PT0001"
    assert ml.photo_uri == "local://var/photos/PT0001/abc123.jpg"
    assert ml.id is None
    assert ml.macros is None
    assert ml.longevity_swap is None


def test_meal_log_analyzed_at_naive() -> None:
    """MealLog.analyzed_at must be timezone-naive."""
    from app.models import MealLog

    ml = MealLog(
        patient_id="PT0001",
        photo_uri="local://var/photos/PT0001/abc123.jpg",
        analyzed_at=datetime(2026, 4, 9, 12, 0, 0),
    )
    assert ml.analyzed_at.tzinfo is None


def test_meal_log_patient_id_indexed() -> None:
    """MealLog must declare an index on patient_id."""
    from app.models import MealLog

    index_names = _get_index_names(MealLog)
    assert any("patient_id" in n for n in index_names), (
        f"No patient_id index on meal_log. Indexes: {index_names}"
    )


# --- SurveyResponse ---

def test_survey_response_instantiable_with_required_fields() -> None:
    """SurveyResponse must be constructable with required fields."""
    from app.models import SurveyResponse

    sr = SurveyResponse(
        patient_id="PT0001",
        kind="onboarding",
        answers={"goal": "live_longer", "sleep_hours": 7},
        submitted_at=datetime(2026, 4, 9, 9, 0, 0),
    )
    assert sr.patient_id == "PT0001"
    assert sr.kind == "onboarding"
    assert sr.answers["goal"] == "live_longer"
    assert sr.id is None


def test_survey_response_kind_values() -> None:
    """SurveyResponse kind must accept onboarding/weekly/quarterly."""
    from app.models import SurveyResponse

    for kind in ("onboarding", "weekly", "quarterly"):
        sr = SurveyResponse(
            patient_id="PT0001",
            kind=kind,
            answers={},
            submitted_at=datetime(2026, 4, 9, 9, 0, 0),
        )
        assert sr.kind == kind


def test_survey_response_submitted_at_naive() -> None:
    """SurveyResponse.submitted_at must be timezone-naive."""
    from app.models import SurveyResponse

    sr = SurveyResponse(
        patient_id="PT0001",
        kind="weekly",
        answers={"energy": 4},
        submitted_at=datetime(2026, 4, 9, 9, 0, 0),
    )
    assert sr.submitted_at.tzinfo is None


def test_survey_response_patient_id_indexed() -> None:
    """SurveyResponse must declare an index on patient_id."""
    from app.models import SurveyResponse

    index_names = _get_index_names(SurveyResponse)
    assert any("patient_id" in n for n in index_names), (
        f"No patient_id index on survey_response. Indexes: {index_names}"
    )


# --- VitalityOutlook ---

def test_vitality_outlook_instantiable_with_required_fields() -> None:
    """VitalityOutlook must be constructable with required fields."""
    from app.models import VitalityOutlook

    vo = VitalityOutlook(
        patient_id="PT0001",
        horizon_months=3,
        projected_score=74.5,
        narrative="Hold your current streak and your outlook improves.",
        computed_at=datetime(2026, 4, 9, 10, 0, 0),
    )
    assert vo.patient_id == "PT0001"
    assert vo.horizon_months == 3
    assert vo.projected_score == 74.5
    assert vo.id is None


def test_vitality_outlook_horizon_months_values() -> None:
    """VitalityOutlook horizon_months must accept 3, 6, or 12."""
    from app.models import VitalityOutlook

    for horizon in (3, 6, 12):
        vo = VitalityOutlook(
            patient_id="PT0001",
            horizon_months=horizon,
            projected_score=70.0,
            narrative="Narrative text.",
            computed_at=datetime(2026, 4, 9, 10, 0, 0),
        )
        assert vo.horizon_months == horizon


def test_vitality_outlook_computed_at_naive() -> None:
    """VitalityOutlook.computed_at must be timezone-naive."""
    from app.models import VitalityOutlook

    vo = VitalityOutlook(
        patient_id="PT0001",
        horizon_months=6,
        projected_score=72.0,
        narrative="Narrative.",
        computed_at=datetime(2026, 4, 9, 10, 0, 0),
    )
    assert vo.computed_at.tzinfo is None


def test_vitality_outlook_patient_id_indexed() -> None:
    """VitalityOutlook must declare an index on patient_id."""
    from app.models import VitalityOutlook

    index_names = _get_index_names(VitalityOutlook)
    assert any("patient_id" in n for n in index_names), (
        f"No patient_id index on vitality_outlook. Indexes: {index_names}"
    )


# --- Message ---

def test_message_instantiable_with_required_fields() -> None:
    """Message must be constructable with required fields."""
    from app.models import Message

    m = Message(
        patient_id="PT0001",
        sender="patient",
        content="Hello, I have a question about my protocol.",
    )
    assert m.patient_id == "PT0001"
    assert m.sender == "patient"
    assert m.content == "Hello, I have a question about my protocol."
    assert m.id is None


def test_message_sender_values() -> None:
    """Message sender must accept 'patient' and 'clinician'."""
    from app.models import Message

    for sender in ("patient", "clinician"):
        msg = Message(
            patient_id="PT0001",
            sender=sender,
            content="Some message.",
        )
        assert msg.sender == sender


def test_message_created_at_naive() -> None:
    """Message.created_at default factory must yield timezone-naive datetime."""
    from app.models import Message

    m = Message(patient_id="PT0001", sender="patient", content="Test.")
    assert m.created_at.tzinfo is None


def test_message_patient_id_indexed() -> None:
    """Message must declare an index on patient_id."""
    from app.models import Message

    index_names = _get_index_names(Message)
    assert any("patient_id" in n for n in index_names), (
        f"No patient_id index on message. Indexes: {index_names}"
    )


# --- Notification ---

def test_notification_instantiable_with_required_fields() -> None:
    """Notification must be constructable with required fields."""
    from app.models import Notification

    n = Notification(
        patient_id="PT0001",
        kind="nudge",
        title="Time for your walk!",
        body="You haven't logged today's protocol action yet.",
    )
    assert n.patient_id == "PT0001"
    assert n.kind == "nudge"
    assert n.title == "Time for your walk!"
    assert n.id is None
    assert n.cta is None
    assert n.delivered_at is None
    assert n.read_at is None


def test_notification_patient_id_indexed() -> None:
    """Notification must declare an index on patient_id."""
    from app.models import Notification

    index_names = _get_index_names(Notification)
    assert any("patient_id" in n for n in index_names), (
        f"No patient_id index on notification. Indexes: {index_names}"
    )


# --- ClinicalReview ---

def test_clinical_review_instantiable_with_required_fields() -> None:
    """ClinicalReview must be constructable with required fields."""
    from app.models import ClinicalReview

    cr = ClinicalReview(
        patient_id="PT0001",
        reason="Elevated ApoB flag requires clinician review.",
        status="pending",
    )
    assert cr.patient_id == "PT0001"
    assert cr.reason == "Elevated ApoB flag requires clinician review."
    assert cr.status == "pending"
    assert cr.id is None
    assert cr.ai_flag is None
    assert cr.clinician_id is None


def test_clinical_review_status_values() -> None:
    """ClinicalReview status must accept pending/in_review/resolved."""
    from app.models import ClinicalReview

    for status in ("pending", "in_review", "resolved"):
        cr = ClinicalReview(
            patient_id="PT0001",
            reason="Some reason.",
            status=status,
        )
        assert cr.status == status


def test_clinical_review_created_at_naive() -> None:
    """ClinicalReview.created_at default must be timezone-naive."""
    from app.models import ClinicalReview

    cr = ClinicalReview(
        patient_id="PT0001", reason="Reason.", status="pending"
    )
    assert cr.created_at.tzinfo is None


def test_clinical_review_patient_id_indexed() -> None:
    """ClinicalReview must declare an index on patient_id."""
    from app.models import ClinicalReview

    index_names = _get_index_names(ClinicalReview)
    assert any("patient_id" in n for n in index_names), (
        f"No patient_id index on clinical_review. Indexes: {index_names}"
    )


# --- Referral ---

def test_referral_instantiable_with_required_fields() -> None:
    """Referral must be constructable with required fields."""
    from app.models import Referral

    r = Referral(
        patient_id="PT0001",
        code="REF-ABCD-1234",
        status="pending",
    )
    assert r.patient_id == "PT0001"
    assert r.code == "REF-ABCD-1234"
    assert r.status == "pending"
    assert r.id is None
    assert r.referred_patient_id is None


def test_referral_created_at_naive() -> None:
    """Referral.created_at default must be timezone-naive."""
    from app.models import Referral

    r = Referral(patient_id="PT0001", code="REF-XYZ", status="pending")
    assert r.created_at.tzinfo is None


def test_referral_patient_id_indexed() -> None:
    """Referral must declare an index on patient_id."""
    from app.models import Referral

    index_names = _get_index_names(Referral)
    assert any("patient_id" in n for n in index_names), (
        f"No patient_id index on referral. Indexes: {index_names}"
    )


# --- Cross-model: no duplicate patient_id indexes ---

def _count_patient_id_indexes(model_cls: object) -> int:
    """Return the number of indexes that cover patient_id on a SQLModel table."""
    return sum(
        1
        for idx in getattr(model_cls, "__table__").indexes
        if any(c.name == "patient_id" for c in idx.columns)
    )


def test_no_duplicate_patient_id_indexes_on_daily_log() -> None:
    from app.models import DailyLog
    count = _count_patient_id_indexes(DailyLog)
    assert count == 1, f"DailyLog has {count} patient_id indexes (expected 1)"


def test_no_duplicate_patient_id_indexes_on_meal_log() -> None:
    from app.models import MealLog
    count = _count_patient_id_indexes(MealLog)
    assert count == 1, f"MealLog has {count} patient_id indexes (expected 1)"


def test_no_duplicate_patient_id_indexes_on_survey_response() -> None:
    from app.models import SurveyResponse
    count = _count_patient_id_indexes(SurveyResponse)
    assert count == 1, f"SurveyResponse has {count} patient_id indexes (expected 1)"


def test_no_duplicate_patient_id_indexes_on_vitality_outlook() -> None:
    from app.models import VitalityOutlook
    count = _count_patient_id_indexes(VitalityOutlook)
    assert count == 1, f"VitalityOutlook has {count} patient_id indexes (expected 1)"


def test_no_duplicate_patient_id_indexes_on_message() -> None:
    from app.models import Message
    count = _count_patient_id_indexes(Message)
    assert count == 1, f"Message has {count} patient_id indexes (expected 1)"


def test_no_duplicate_patient_id_indexes_on_notification() -> None:
    from app.models import Notification
    count = _count_patient_id_indexes(Notification)
    assert count == 1, f"Notification has {count} patient_id indexes (expected 1)"


def test_no_duplicate_patient_id_indexes_on_clinical_review() -> None:
    from app.models import ClinicalReview
    count = _count_patient_id_indexes(ClinicalReview)
    assert count == 1, f"ClinicalReview has {count} patient_id indexes (expected 1)"


def test_no_duplicate_patient_id_indexes_on_referral() -> None:
    from app.models import Referral
    count = _count_patient_id_indexes(Referral)
    assert count == 1, f"Referral has {count} patient_id indexes (expected 1)"


# --- JSONB column types ---

def test_survey_response_answers_column_type() -> None:
    """SurveyResponse.answers must be backed by a JSONB or JSON column."""
    from app.models import SurveyResponse
    from sqlalchemy.dialects.postgresql import JSONB
    from sqlalchemy import JSON

    col = SurveyResponse.__table__.c["answers"]
    assert isinstance(col.type, (JSONB, JSON)), (
        f"Expected JSONB/JSON, got: {type(col.type)}"
    )


def test_meal_log_macros_column_type() -> None:
    """MealLog.macros must be backed by a JSONB or JSON column (nullable)."""
    from app.models import MealLog
    from sqlalchemy.dialects.postgresql import JSONB
    from sqlalchemy import JSON

    col = MealLog.__table__.c["macros"]
    assert isinstance(col.type, (JSONB, JSON)), (
        f"Expected JSONB/JSON, got: {type(col.type)}"
    )
