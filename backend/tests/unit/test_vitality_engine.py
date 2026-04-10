"""Unit tests for the vitality_engine service.

Pure-function tests — no database access.  All fixtures are constructed
in-memory from the dataclass/SQLModel model shapes.

Golden values were computed by hand against the piecewise-linear anchors
documented in docs/10-vitality-formula.md.  When in doubt, re-derive from
the spec — do not tune anchors to hit round numbers.
"""

from __future__ import annotations

import datetime

import pytest

from app.models import EHRRecord, LifestyleProfile, Patient, WearableDay
from app.services.vitality_engine import (
    DISCLAIMER,
    SCORING_WINDOW_DAYS,
    TREND_WINDOW_DAYS,
    TrendPoint,
    VitalityResult,
    _lerp,
    compute_vitality,
)

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
    sleep_satisfaction: int | None = None,
) -> LifestyleProfile:
    return LifestyleProfile(
        patient_id=patient_id,
        survey_date=datetime.date(2024, 9, 1),
        diet_quality_score=diet_quality_score,
        exercise_sessions_weekly=exercise_sessions_weekly,
        stress_level=stress_level,
        sleep_satisfaction=sleep_satisfaction,
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
# Tests: _lerp helper
# ---------------------------------------------------------------------------

_SIMPLE_ANCHORS = [(0.0, 0.0), (10.0, 100.0)]


def test_lerp_below_first_anchor_clamps_to_first_output() -> None:
    """Input below the first anchor returns the first output (clamp low)."""
    assert _lerp(_SIMPLE_ANCHORS, -5.0) == pytest.approx(0.0)
    assert _lerp(_SIMPLE_ANCHORS, 0.0) == pytest.approx(0.0)


def test_lerp_above_last_anchor_clamps_to_last_output() -> None:
    """Input above the last anchor returns the last output (clamp high)."""
    assert _lerp(_SIMPLE_ANCHORS, 15.0) == pytest.approx(100.0)
    assert _lerp(_SIMPLE_ANCHORS, 10.0) == pytest.approx(100.0)


def test_lerp_midpoint_between_anchors() -> None:
    """Midpoint between two anchors returns the midpoint output."""
    assert _lerp(_SIMPLE_ANCHORS, 5.0) == pytest.approx(50.0)


def test_lerp_exact_anchor_value() -> None:
    """Input exactly on an anchor returns its mapped output."""
    multi = [(0.0, 10.0), (5.0, 50.0), (10.0, 90.0)]
    assert _lerp(multi, 5.0) == pytest.approx(50.0)


def test_lerp_single_anchor_returns_that_output() -> None:
    """A single-anchor table always returns its output regardless of input."""
    single = [(5.0, 42.0)]
    assert _lerp(single, 0.0) == pytest.approx(42.0)
    assert _lerp(single, 5.0) == pytest.approx(42.0)
    assert _lerp(single, 100.0) == pytest.approx(42.0)


def test_lerp_sleep_duration_anchors() -> None:
    """Verify a few manually computed points on the sleep duration anchor table.

    Anchors: (4→20), (6→55), (7.5→95), (9→80), (10→55)
    """
    sleep_anchors = [(4.0, 20.0), (6.0, 55.0), (7.5, 95.0), (9.0, 80.0), (10.0, 55.0)]
    # Exact anchors
    assert _lerp(sleep_anchors, 4.0) == pytest.approx(20.0)
    assert _lerp(sleep_anchors, 6.0) == pytest.approx(55.0)
    assert _lerp(sleep_anchors, 7.5) == pytest.approx(95.0)
    assert _lerp(sleep_anchors, 9.0) == pytest.approx(80.0)
    assert _lerp(sleep_anchors, 10.0) == pytest.approx(55.0)
    # Between 6 → 7.5: f=(7.4-6)/(7.5-6)=1.4/1.5=0.933; 55+0.933*40 = 92.3
    assert _lerp(sleep_anchors, 7.4) == pytest.approx(92.3, abs=0.1)
    # Clamping
    assert _lerp(sleep_anchors, 3.0) == pytest.approx(20.0)
    assert _lerp(sleep_anchors, 11.0) == pytest.approx(55.0)


# ---------------------------------------------------------------------------
# Tests: subscore fallbacks
# ---------------------------------------------------------------------------


def test_sleep_fallback_on_empty_wearable() -> None:
    """Sleep subscore must return 50 when wearable list is empty."""
    result = compute_vitality(
        patient=_patient(),
        ehr=[_lab_panel_record()],
        wearable=[],
        lifestyle=_lifestyle(),
    )
    assert result.subscores["sleep"] == pytest.approx(50.0)


def test_activity_fallback_on_empty_wearable() -> None:
    """Activity subscore must return 30 when wearable list is empty."""
    result = compute_vitality(
        patient=_patient(),
        ehr=[_lab_panel_record()],
        wearable=[],
        lifestyle=_lifestyle(),
    )
    assert result.subscores["activity"] == pytest.approx(30.0)


def test_metabolic_fallback_on_empty_lab() -> None:
    """Metabolic subscore must return 65 when no lab panel is available."""
    result = compute_vitality(
        patient=_patient(),
        ehr=[],
        wearable=_seven_wearable_days(),
        lifestyle=_lifestyle(),
    )
    assert result.subscores["metabolic"] == pytest.approx(65.0)


def test_lifestyle_fallback_on_missing_profile() -> None:
    """Lifestyle subscore must return 60 when no LifestyleProfile is provided."""
    result = compute_vitality(
        patient=_patient(),
        ehr=[_lab_panel_record()],
        wearable=_seven_wearable_days(),
        lifestyle=None,
    )
    assert result.subscores["lifestyle"] == pytest.approx(60.0)


def test_cardio_fallback_on_no_data() -> None:
    """Cardio subscore must return 65 when labs are missing and wearable has no HR."""
    result = compute_vitality(
        patient=_patient(),
        ehr=[],
        wearable=[
            _wearable_day(date=_BASE_DATE - datetime.timedelta(days=i), resting_hr_bpm=None)
            for i in range(7)
        ],
        lifestyle=None,
    )
    assert result.subscores["cardio"] == pytest.approx(65.0)


# ---------------------------------------------------------------------------
# Tests: subscore golden values — default fixture
# ---------------------------------------------------------------------------
# Default wearable: steps=8000, active_minutes=30/day, sleep_duration=7.5h,
#   sleep_quality=75, deep_sleep_pct=20.0, resting_hr=65
# Default lab: ldl=2.4, sbp=115, hba1c=5.2, fasting_glucose=5.0, crp=0.5
# Default lifestyle: diet=7, exercise=3, stress=3, sleep_satisfaction=None


def test_sleep_subscore_golden_value() -> None:
    """Sleep subscore for default 7-day fixture.

    duration_score(7.5) = 95 (exact anchor)
    quality_avg = (95 + 75) / 2 = 85.0
    deep_sleep_pct=20 >= 20 → +5 → 90.0
    """
    result = compute_vitality(
        patient=_patient(),
        ehr=[_lab_panel_record()],
        wearable=_seven_wearable_days(),
        lifestyle=_lifestyle(),
    )
    assert result.subscores["sleep"] == pytest.approx(90.0, abs=0.5)


def test_activity_subscore_golden_value() -> None:
    """Activity subscore for default 7-day fixture.

    Weekly mins = 30*7 = 210; lerp at 210 → 91.0
    Steps avg = 8000; lerp at 8000 → 85.0 (exact anchor)
    activity = (91.0 + 85.0) / 2 = 88.0
    """
    result = compute_vitality(
        patient=_patient(),
        ehr=[_lab_panel_record()],
        wearable=_seven_wearable_days(),
        lifestyle=_lifestyle(),
    )
    assert result.subscores["activity"] == pytest.approx(88.0, abs=0.5)


def test_metabolic_subscore_golden_value() -> None:
    """Metabolic subscore for default lab fixture.

    hba1c=5.2: f=(5.2-5.0)/(5.7-5.0)=0.2857; 100+0.2857*(85-100)=95.71
    fasting_glucose=5.0: f=(5.0-4.5)/(5.6-4.5)=0.4545; 100+0.4545*(85-100)=93.18
    crp=0.5: exact anchor → 100.0
    metabolic = (95.71 + 93.18 + 100.0) / 3 ≈ 96.3
    """
    result = compute_vitality(
        patient=_patient(),
        ehr=[_lab_panel_record()],
        wearable=_seven_wearable_days(),
        lifestyle=_lifestyle(),
    )
    assert result.subscores["metabolic"] == pytest.approx(96.3, abs=0.5)


def test_cardio_subscore_golden_value() -> None:
    """Cardio subscore for default lab + wearable fixture.

    ldl=2.4: f=(2.4-2.0)/(2.6-2.0)=0.667; 100+0.667*(85-100)=90.0
    sbp=115: f=(115-110)/(120-110)=0.5; 100+0.5*(90-100)=95.0
    resting_hr=65: f=(65-60)/(70-60)=0.5; 90+0.5*(75-90)=82.5
    cardio = (90.0 + 95.0 + 82.5) / 3 ≈ 89.2
    """
    result = compute_vitality(
        patient=_patient(),
        ehr=[_lab_panel_record()],
        wearable=_seven_wearable_days(),
        lifestyle=_lifestyle(),
    )
    assert result.subscores["cardio"] == pytest.approx(89.2, abs=0.5)


def test_lifestyle_subscore_golden_value() -> None:
    """Lifestyle subscore for default fixture (no sleep_satisfaction).

    diet=7: 7*10=70
    exercise=3: lerp(2→65,4→90) at 3: 65+0.5*(90-65)=77.5
    stress=3 (inverted): lerp(1→100,5→60) at 3: 100+0.5*(60-100)=80.0
    No sleep_satisfaction → excluded
    lifestyle = (70 + 77.5 + 80) / 3 ≈ 75.8
    """
    result = compute_vitality(
        patient=_patient(),
        ehr=[_lab_panel_record()],
        wearable=_seven_wearable_days(),
        lifestyle=_lifestyle(),
    )
    assert result.subscores["lifestyle"] == pytest.approx(75.8, abs=0.5)


def test_lifestyle_subscore_with_sleep_satisfaction() -> None:
    """Lifestyle subscore when sleep_satisfaction is provided.

    diet=7: 70; exercise=3: 77.5; stress=3: 80; sleep_satisfaction=8: 80
    lifestyle = (70 + 77.5 + 80 + 80) / 4 = 76.875
    """
    result = compute_vitality(
        patient=_patient(),
        ehr=[_lab_panel_record()],
        wearable=_seven_wearable_days(),
        lifestyle=_lifestyle(sleep_satisfaction=8),
    )
    assert result.subscores["lifestyle"] == pytest.approx(76.875, abs=0.5)


def test_composite_score_golden_value() -> None:
    """Composite score for default fixtures.

    sleep=90.0, activity=88.0, metabolic=96.3, cardio=89.2, lifestyle=75.8
    0.20*90 + 0.20*88 + 0.20*96.3 + 0.25*89.2 + 0.15*75.8
    = 18.0 + 17.6 + 19.26 + 22.3 + 11.37 = 88.53
    """
    result = compute_vitality(
        patient=_patient(),
        ehr=[_lab_panel_record()],
        wearable=_seven_wearable_days(),
        lifestyle=_lifestyle(),
    )
    assert result.score == pytest.approx(88.5, abs=1.0)


# ---------------------------------------------------------------------------
# Tests: Rebecca golden values (from doc section 6)
# ---------------------------------------------------------------------------


def _rebecca_wearable() -> list[WearableDay]:
    """7-day wearable fixture matching Rebecca's day-90 profile in the spec."""
    return [
        WearableDay(
            patient_id="PT0199",
            date=datetime.date(2026, 4, 10) - datetime.timedelta(days=i),
            steps=9200,
            active_minutes=33,
            sleep_duration_hrs=7.4,
            sleep_quality_score=82.0,
            deep_sleep_pct=21.0,
            resting_hr_bpm=65,
        )
        for i in range(7)
    ]


def _rebecca_ehr() -> list[EHRRecord]:
    """Lab panel matching Rebecca's day-90 labs in the spec."""
    return [
        EHRRecord(
            patient_id="PT0199",
            record_type="lab_panel",
            recorded_at=datetime.datetime(2026, 4, 5),
            source="csv",
            payload={
                "hba1c_pct": 6.5,
                "fasting_glucose_mmol": 7.4,
                "sbp_mmhg": 132.0,
                "ldl_mmol": 2.9,
                "crp_mg_l": 1.8,
            },
        )
    ]


def _rebecca_lifestyle() -> LifestyleProfile:
    """Lifestyle survey matching Rebecca's day-90 survey in the spec."""
    return LifestyleProfile(
        patient_id="PT0199",
        survey_date=datetime.date(2026, 4, 5),
        diet_quality_score=8,
        exercise_sessions_weekly=5,
        stress_level=4,
        sleep_satisfaction=8,
    )


def test_rebecca_sleep_subscore() -> None:
    """Rebecca sleep subscore = 92.2 per worked example in spec section 6.2."""
    result = compute_vitality(
        patient=_patient(patient_id="PT0199"),
        ehr=_rebecca_ehr(),
        wearable=_rebecca_wearable(),
        lifestyle=_rebecca_lifestyle(),
    )
    assert result.subscores["sleep"] == pytest.approx(92.2, abs=0.5)


def test_rebecca_activity_subscore() -> None:
    """Rebecca activity subscore = 91.3 per worked example in spec section 6.3."""
    result = compute_vitality(
        patient=_patient(patient_id="PT0199"),
        ehr=_rebecca_ehr(),
        wearable=_rebecca_wearable(),
        lifestyle=_rebecca_lifestyle(),
    )
    assert result.subscores["activity"] == pytest.approx(91.3, abs=0.5)


def test_rebecca_metabolic_subscore() -> None:
    """Rebecca metabolic subscore = 59.5 per worked example in spec section 6.4."""
    result = compute_vitality(
        patient=_patient(patient_id="PT0199"),
        ehr=_rebecca_ehr(),
        wearable=_rebecca_wearable(),
        lifestyle=_rebecca_lifestyle(),
    )
    assert result.subscores["metabolic"] == pytest.approx(59.5, abs=0.5)


def test_rebecca_cardio_subscore() -> None:
    """Rebecca cardio subscore = 73.9 per worked example in spec section 6.5."""
    result = compute_vitality(
        patient=_patient(patient_id="PT0199"),
        ehr=_rebecca_ehr(),
        wearable=_rebecca_wearable(),
        lifestyle=_rebecca_lifestyle(),
    )
    assert result.subscores["cardio"] == pytest.approx(73.9, abs=0.5)


def test_rebecca_lifestyle_subscore() -> None:
    """Rebecca lifestyle subscore = 81.25 per worked example in spec section 6.6."""
    result = compute_vitality(
        patient=_patient(patient_id="PT0199"),
        ehr=_rebecca_ehr(),
        wearable=_rebecca_wearable(),
        lifestyle=_rebecca_lifestyle(),
    )
    assert result.subscores["lifestyle"] == pytest.approx(81.25, abs=0.5)


def test_rebecca_composite_score() -> None:
    """Rebecca composite = ~79.3 per worked example in spec section 6.7."""
    result = compute_vitality(
        patient=_patient(patient_id="PT0199"),
        ehr=_rebecca_ehr(),
        wearable=_rebecca_wearable(),
        lifestyle=_rebecca_lifestyle(),
    )
    assert result.score == pytest.approx(79.3, abs=1.0)


# ---------------------------------------------------------------------------
# Tests: original structural tests (updated for 30-day trend window)
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


def test_compute_vitality_trend_length_capped_at_30() -> None:
    """Trend length equals min(len(wearable), TREND_WINDOW_DAYS).

    TREND_WINDOW_DAYS = 30; SCORING_WINDOW_DAYS = 7 (for subscores only).
    """
    assert SCORING_WINDOW_DAYS == 7
    assert TREND_WINDOW_DAYS == 30

    # 5 wearable days → 5 trend points
    five_days = [
        _wearable_day(date=_BASE_DATE - datetime.timedelta(days=i)) for i in range(5)
    ]
    result5 = compute_vitality(
        patient=_patient(),
        ehr=[_lab_panel_record()],
        wearable=five_days,
        lifestyle=_lifestyle(),
    )
    assert len(result5.trend) == 5
    assert all(isinstance(p, TrendPoint) for p in result5.trend)

    # 7 wearable days → 7 trend points
    result7 = compute_vitality(
        patient=_patient(),
        ehr=[_lab_panel_record()],
        wearable=_seven_wearable_days(),
        lifestyle=_lifestyle(),
    )
    assert len(result7.trend) == 7

    # 35 wearable days → capped at 30
    thirty_five_days = [
        _wearable_day(date=_BASE_DATE - datetime.timedelta(days=i)) for i in range(35)
    ]
    result35 = compute_vitality(
        patient=_patient(),
        ehr=[_lab_panel_record()],
        wearable=thirty_five_days,
        lifestyle=_lifestyle(),
    )
    assert len(result35.trend) == 30


def test_compute_vitality_handles_missing_wearable() -> None:
    """Empty wearable list must not crash; trend is empty; fallbacks apply."""
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

    Real numbers: LDL 3.84 mmol/L (>=3.0 threshold) and total cholesterol
    7.05 mmol/L (>=6.5 threshold).  Both flags must appear in risk_flags.
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


def test_compute_vitality_trend_newest_first() -> None:
    """Trend array must be ordered newest-first."""
    result = compute_vitality(
        patient=_patient(),
        ehr=[_lab_panel_record()],
        wearable=_seven_wearable_days(),
        lifestyle=_lifestyle(),
    )
    dates = [p.date for p in result.trend]
    assert dates == sorted(dates, reverse=True), "Trend must be newest-first"


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


def test_composite_clamped_to_0_100() -> None:
    """Composite score must be clamped to [0, 100]."""
    # Use absurd inputs that would push scores near extremes
    result = compute_vitality(
        patient=_patient(),
        ehr=[
            _lab_panel_record(
                hba1c_pct=9.0,
                fasting_glucose_mmol=9.0,
                crp_mg_l=10.0,
                ldl_mmol=5.0,
                sbp_mmhg=160.0,
            )
        ],
        wearable=[
            _wearable_day(
                date=_BASE_DATE - datetime.timedelta(days=i),
                steps=0,
                active_minutes=0,
                sleep_duration_hrs=4.0,
                sleep_quality_score=0.0,
                resting_hr_bpm=90,
                deep_sleep_pct=5.0,
            )
            for i in range(7)
        ],
        lifestyle=_lifestyle(diet_quality_score=1, exercise_sessions_weekly=0, stress_level=10),
    )
    assert 0.0 <= result.score <= 100.0
