"""Unit tests for the vitality_engine service.

Pure-function tests — no database access.  All fixtures are constructed
in-memory from the dataclass/SQLModel model shapes.
"""

from __future__ import annotations

import datetime

import pytest

from app.models import EHRRecord, LifestyleProfile, Patient, WearableDay
from app.services.vitality_engine import DISCLAIMER, TrendPoint, VitalityResult, compute_vitality

# ---------------------------------------------------------------------------
# Shared fixture helpers
# ---------------------------------------------------------------------------

_BASE_DATE = datetime.date(2024, 10, 1)


def _patient(
    patient_id: str = "PT0001",
    age: int = 40,
    sex: str = "M",
    bmi: float | None = 24.0,
) -> Patient:
    return Patient(
        patient_id=patient_id,
        name="Test Patient",
        age=age,
        sex=sex,
        country="DE",
        bmi=bmi,
    )


def _lab_panel_record(
    patient_id: str = "PT0001",
    *,
    total_cholesterol_mmol: float = 5.0,
    ldl_mmol: float = 2.4,
    hdl_mmol: float = 1.5,
    triglycerides_mmol: float = 1.0,
    hba1c_pct: float = 5.2,
    fasting_glucose_mmol: float = 5.0,
    crp_mg_l: float = 0.5,
    egfr_ml_min: float = 90.0,
    sbp_mmhg: float = 115.0,
    dbp_mmhg: float = 75.0,
) -> EHRRecord:
    return EHRRecord(
        patient_id=patient_id,
        record_type="lab_panel",
        recorded_at=datetime.datetime(2024, 9, 1),
        source="csv",
        payload={
            "total_cholesterol_mmol": total_cholesterol_mmol,
            "ldl_mmol": ldl_mmol,
            "hdl_mmol": hdl_mmol,
            "triglycerides_mmol": triglycerides_mmol,
            "hba1c_pct": hba1c_pct,
            "fasting_glucose_mmol": fasting_glucose_mmol,
            "crp_mg_l": crp_mg_l,
            "egfr_ml_min": egfr_ml_min,
            "sbp_mmhg": sbp_mmhg,
            "dbp_mmhg": dbp_mmhg,
        },
    )


def _wearable_day(
    patient_id: str = "PT0001",
    date: datetime.date | None = None,
    *,
    resting_hr_bpm: int | None = 65,
    steps: int | None = 8000,
    active_minutes: int | None = 30,
    sleep_duration_hrs: float | None = 7.5,
    sleep_quality_score: float | None = 75.0,
    deep_sleep_pct: float | None = 20.0,
) -> WearableDay:
    if date is None:
        date = _BASE_DATE
    return WearableDay(
        patient_id=patient_id,
        date=date,
        resting_hr_bpm=resting_hr_bpm,
        steps=steps,
        active_minutes=active_minutes,
        sleep_duration_hrs=sleep_duration_hrs,
        sleep_quality_score=sleep_quality_score,
        deep_sleep_pct=deep_sleep_pct,
    )


def _lifestyle(
    patient_id: str = "PT0001",
    *,
    diet_quality_score: int | None = 7,
    exercise_sessions_weekly: int | None = 3,
    stress_level: int | None = 3,
) -> LifestyleProfile:
    return LifestyleProfile(
        patient_id=patient_id,
        survey_date=datetime.date(2024, 9, 1),
        diet_quality_score=diet_quality_score,
        exercise_sessions_weekly=exercise_sessions_weekly,
        stress_level=stress_level,
    )


def _seven_wearable_days(patient_id: str = "PT0001") -> list[WearableDay]:
    """7 wearable days (newest-first ordering)."""
    return [
        _wearable_day(patient_id=patient_id, date=_BASE_DATE - datetime.timedelta(days=i))
        for i in range(7)
    ]


# ---------------------------------------------------------------------------
# Anna (PT0282) fixture — matches real CSV numbers exactly
# ---------------------------------------------------------------------------

_ANNA_PATIENT = _patient(patient_id="PT0282", age=43, sex="F", bmi=22.7)

_ANNA_LAB = _lab_panel_record(
    patient_id="PT0282",
    total_cholesterol_mmol=7.05,
    ldl_mmol=3.84,
    hdl_mmol=1.42,
    triglycerides_mmol=1.3,
    hba1c_pct=5.3,
    fasting_glucose_mmol=5.1,
    crp_mg_l=0.8,
    egfr_ml_min=88.0,
    sbp_mmhg=128.0,
    dbp_mmhg=82.0,
)

_ANNA_WEARABLE = _seven_wearable_days("PT0282")

_ANNA_LIFESTYLE = _lifestyle("PT0282", diet_quality_score=7, exercise_sessions_weekly=3, stress_level=4)

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_compute_vitality_returns_score_in_range_0_100() -> None:
    """Overall score must fall within [0, 100]."""
    result = compute_vitality(
        patient=_patient(),
        ehr=[_lab_panel_record()],
        wearable=_seven_wearable_days(),
        lifestyle=_lifestyle(),
    )
    assert isinstance(result, VitalityResult)
    assert 0.0 <= result.score <= 100.0


def test_compute_vitality_subscores_keys() -> None:
    """Subscores dict must contain exactly the five documented dimensions."""
    result = compute_vitality(
        patient=_patient(),
        ehr=[_lab_panel_record()],
        wearable=_seven_wearable_days(),
        lifestyle=_lifestyle(),
    )
    assert set(result.subscores.keys()) == {"sleep", "activity", "metabolic", "cardio", "lifestyle"}
    for v in result.subscores.values():
        assert 0.0 <= v <= 100.0, f"Subscore out of range: {v}"


def test_compute_vitality_trend_length_matches_input_days_up_to_7() -> None:
    """Trend length equals min(len(wearable), 7)."""
    # 5 wearable days → 5 trend points
    five_days = _seven_wearable_days()[:5]
    result = compute_vitality(
        patient=_patient(),
        ehr=[_lab_panel_record()],
        wearable=five_days,
        lifestyle=_lifestyle(),
    )
    assert len(result.trend) == 5
    assert all(isinstance(p, TrendPoint) for p in result.trend)

    # 7 wearable days → 7 trend points
    result7 = compute_vitality(
        patient=_patient(),
        ehr=[_lab_panel_record()],
        wearable=_seven_wearable_days(),
        lifestyle=_lifestyle(),
    )
    assert len(result7.trend) == 7

    # More than 7 days → capped at 7
    ten_days = [
        _wearable_day(date=_BASE_DATE - datetime.timedelta(days=i)) for i in range(10)
    ]
    result10 = compute_vitality(
        patient=_patient(),
        ehr=[_lab_panel_record()],
        wearable=ten_days,
        lifestyle=_lifestyle(),
    )
    assert len(result10.trend) == 7


def test_compute_vitality_handles_missing_wearable() -> None:
    """Empty wearable list must not crash; score is still a float in [0, 100]."""
    result = compute_vitality(
        patient=_patient(),
        ehr=[_lab_panel_record()],
        wearable=[],
        lifestyle=_lifestyle(),
    )
    assert isinstance(result.score, float)
    assert 0.0 <= result.score <= 100.0
    assert result.trend == []


def test_compute_vitality_handles_missing_lab_panel() -> None:
    """No lab_panel EHR records must not crash; score is still valid."""
    result = compute_vitality(
        patient=_patient(),
        ehr=[],
        wearable=_seven_wearable_days(),
        lifestyle=_lifestyle(),
    )
    assert isinstance(result.score, float)
    assert 0.0 <= result.score <= 100.0


def test_compute_vitality_disclaimer_present() -> None:
    """Result must carry the module-level DISCLAIMER constant."""
    result = compute_vitality(
        patient=_patient(),
        ehr=[_lab_panel_record()],
        wearable=_seven_wearable_days(),
        lifestyle=_lifestyle(),
    )
    assert result.disclaimer == DISCLAIMER
    assert "not medical advice" in result.disclaimer.lower()


def test_compute_vitality_anna_flags_ldl_and_cholesterol() -> None:
    """PT0282 (Anna Weber) must surface both lipid risk flags.

    Real numbers: LDL 3.84 mmol/L (≥3.0 threshold) and total cholesterol
    7.05 mmol/L (≥6.5 threshold).  Both flags must appear in risk_flags.
    """
    result = compute_vitality(
        patient=_ANNA_PATIENT,
        ehr=[_ANNA_LAB],
        wearable=_ANNA_WEARABLE,
        lifestyle=_ANNA_LIFESTYLE,
    )
    assert "lipid_ldl_elevated" in result.risk_flags, (
        f"Expected lipid_ldl_elevated in {result.risk_flags}"
    )
    assert "lipid_cholesterol_elevated" in result.risk_flags, (
        f"Expected lipid_cholesterol_elevated in {result.risk_flags}"
    )


def test_compute_vitality_anna_borderline_bp_flag() -> None:
    """Anna's SBP 128 must trigger bp_borderline_elevated."""
    result = compute_vitality(
        patient=_ANNA_PATIENT,
        ehr=[_ANNA_LAB],
        wearable=_ANNA_WEARABLE,
        lifestyle=_ANNA_LIFESTYLE,
    )
    assert "bp_borderline_elevated" in result.risk_flags, (
        f"Expected bp_borderline_elevated in {result.risk_flags}"
    )


def test_compute_vitality_trend_scores_in_range() -> None:
    """Each TrendPoint.score must be in [0, 100]."""
    result = compute_vitality(
        patient=_patient(),
        ehr=[_lab_panel_record()],
        wearable=_seven_wearable_days(),
        lifestyle=_lifestyle(),
    )
    for point in result.trend:
        assert 0.0 <= point.score <= 100.0, f"Trend score out of range: {point.score}"


def test_compute_vitality_no_flags_for_healthy_patient() -> None:
    """Patient with excellent vitality markers should produce zero risk flags."""
    result = compute_vitality(
        patient=_patient(),
        ehr=[
            _lab_panel_record(
                ldl_mmol=1.5,
                total_cholesterol_mmol=4.0,
                hba1c_pct=5.0,
                fasting_glucose_mmol=4.8,
                sbp_mmhg=112.0,
            )
        ],
        wearable=[
            _wearable_day(
                date=_BASE_DATE - datetime.timedelta(days=i),
                sleep_duration_hrs=7.5,
                active_minutes=25,
                resting_hr_bpm=58,
            )
            for i in range(7)
        ],
        lifestyle=_lifestyle(
            diet_quality_score=9,
            exercise_sessions_weekly=5,
            stress_level=2,
        ),
    )
    assert result.risk_flags == []
