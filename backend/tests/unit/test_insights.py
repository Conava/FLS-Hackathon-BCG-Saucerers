"""Unit tests for the insights service.

Pure-function tests — no database access.
Verifies wellness-framing compliance (MDR/legal requirement) and
correct insight derivation from VitalityResult.
"""

from __future__ import annotations

import datetime
import re

import pytest

from app.models import EHRRecord, LifestyleProfile, Patient, WearableDay
from app.services.insights import Insight, derive_insights
from app.services.vitality_engine import DISCLAIMER, TrendPoint, VitalityResult

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

_DIAGNOSTIC_VERB_RE = re.compile(r"diagnos|treat|cure|disease", re.IGNORECASE)

_BASE_DATE = datetime.date(2024, 10, 1)


def _make_vitality(
    score: float = 72.0,
    subscores: dict[str, float] | None = None,
    risk_flags: list[str] | None = None,
) -> VitalityResult:
    """Build a minimal VitalityResult for testing."""
    if subscores is None:
        subscores = {
            "sleep": 75.0,
            "activity": 70.0,
            "metabolic": 80.0,
            "cardio": 65.0,
            "lifestyle": 70.0,
        }
    return VitalityResult(
        score=score,
        subscores=subscores,
        risk_flags=risk_flags if risk_flags is not None else [],
        trend=[TrendPoint(date=_BASE_DATE - datetime.timedelta(days=i), score=72.0) for i in range(7)],
        disclaimer=DISCLAIMER,
    )


def _lab_panel(
    patient_id: str = "PT0001",
    **payload_overrides: float,
) -> EHRRecord:
    payload: dict[str, float] = {
        "total_cholesterol_mmol": 5.0,
        "ldl_mmol": 2.4,
        "hdl_mmol": 1.5,
        "triglycerides_mmol": 1.0,
        "hba1c_pct": 5.2,
        "fasting_glucose_mmol": 5.0,
        "crp_mg_l": 0.5,
        "egfr_ml_min": 90.0,
        "sbp_mmhg": 115.0,
        "dbp_mmhg": 75.0,
    }
    payload.update(payload_overrides)
    return EHRRecord(
        patient_id=patient_id,
        record_type="lab_panel",
        recorded_at=datetime.datetime(2024, 9, 1),
        source="csv",
        payload=payload,
    )


def _lifestyle(
    patient_id: str = "PT0001",
    *,
    stress_level: int | None = 3,
    exercise_sessions_weekly: int | None = 3,
    diet_quality_score: int | None = 7,
) -> LifestyleProfile:
    return LifestyleProfile(
        patient_id=patient_id,
        survey_date=datetime.date(2024, 9, 1),
        diet_quality_score=diet_quality_score,
        exercise_sessions_weekly=exercise_sessions_weekly,
        stress_level=stress_level,
    )


# Anna (PT0282) fixture
_ANNA_VITALITY = _make_vitality(
    score=68.0,
    subscores={
        "sleep": 75.0,
        "activity": 72.0,
        "metabolic": 82.0,
        "cardio": 55.0,
        "lifestyle": 65.0,
    },
    risk_flags=[
        "lipid_ldl_elevated",
        "lipid_cholesterol_elevated",
        "bp_borderline_elevated",
    ],
)

_ANNA_LAB = _lab_panel(
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

_ANNA_LIFESTYLE = _lifestyle("PT0282", stress_level=4, exercise_sessions_weekly=3, diet_quality_score=7)

# ---------------------------------------------------------------------------
# Wellness-framing compliance tests (HARD REQUIREMENT — MDR / legal)
# ---------------------------------------------------------------------------


def test_insights_wellness_framing() -> None:
    """No Insight message, signal, or prevention string may contain diagnostic verbs.

    Forbidden terms: diagnos*, treat*, cure*, disease*
    """
    insights = derive_insights(
        vitality=_ANNA_VITALITY,
        ehr=[_ANNA_LAB],
        lifestyle=_ANNA_LIFESTYLE,
    )
    # Test should also run on the unhealthy fixture that maximises output
    for insight in insights:
        for text in [insight.message, *insight.signals, *insight.prevention_signals]:
            assert _DIAGNOSTIC_VERB_RE.search(text) is None, (
                f"Diagnostic verb found in insight text: {text!r}"
            )


def test_insights_wellness_framing_all_flags() -> None:
    """Run all possible flags through insights and check framing for each."""
    all_flags_vitality = _make_vitality(
        risk_flags=[
            "lipid_ldl_elevated",
            "lipid_cholesterol_elevated",
            "bp_borderline_elevated",
            "sleep_duration_low",
            "activity_low",
            "metabolic_hba1c_elevated",
        ]
    )
    all_flags_lab = _lab_panel(
        ldl_mmol=4.5,
        total_cholesterol_mmol=7.5,
        sbp_mmhg=135.0,
        hba1c_pct=6.0,
    )
    insights = derive_insights(
        vitality=all_flags_vitality,
        ehr=[all_flags_lab],
        lifestyle=_lifestyle(),
    )
    for insight in insights:
        for text in [insight.message, *insight.signals, *insight.prevention_signals]:
            assert _DIAGNOSTIC_VERB_RE.search(text) is None, (
                f"Diagnostic verb found in insight text: {text!r}"
            )


# ---------------------------------------------------------------------------
# Functional correctness tests
# ---------------------------------------------------------------------------


def test_insights_anna_returns_cardiovascular_insight() -> None:
    """Anna's lipid flags must produce at least one cardiovascular Insight
    with severity 'moderate' or 'high'.
    """
    insights = derive_insights(
        vitality=_ANNA_VITALITY,
        ehr=[_ANNA_LAB],
        lifestyle=_ANNA_LIFESTYLE,
    )
    cardio_insights = [i for i in insights if i.kind == "cardiovascular"]
    assert cardio_insights, "Expected at least one cardiovascular Insight for Anna"
    severities = {i.severity for i in cardio_insights}
    assert severities & {"moderate", "high"}, (
        f"Expected moderate or high severity cardiovascular insight, got: {severities}"
    )


def test_insights_empty_when_everything_healthy() -> None:
    """Healthy fixture with no risk flags must return no high/moderate insights."""
    healthy_vitality = _make_vitality(
        score=90.0,
        subscores={
            "sleep": 90.0,
            "activity": 90.0,
            "metabolic": 90.0,
            "cardio": 90.0,
            "lifestyle": 90.0,
        },
        risk_flags=[],
    )
    insights = derive_insights(
        vitality=healthy_vitality,
        ehr=[],
        lifestyle=_lifestyle(),
    )
    # Either empty list, or only low severity
    non_low = [i for i in insights if i.severity in {"moderate", "high"}]
    assert non_low == [], f"Unexpected moderate/high insights for healthy patient: {non_low}"


def test_insights_returns_list_of_insight() -> None:
    """Return type must be a list of Insight dataclass instances."""
    insights = derive_insights(
        vitality=_ANNA_VITALITY,
        ehr=[_ANNA_LAB],
        lifestyle=_ANNA_LIFESTYLE,
    )
    assert isinstance(insights, list)
    for item in insights:
        assert isinstance(item, Insight)


def test_insights_has_required_fields() -> None:
    """Every Insight must have non-empty kind, severity, message, signals, prevention_signals."""
    insights = derive_insights(
        vitality=_ANNA_VITALITY,
        ehr=[_ANNA_LAB],
        lifestyle=_ANNA_LIFESTYLE,
    )
    for insight in insights:
        assert insight.kind, "Insight.kind must not be empty"
        assert insight.severity in {"low", "moderate", "high"}, (
            f"Invalid severity: {insight.severity}"
        )
        assert insight.message, "Insight.message must not be empty"
        assert isinstance(insight.signals, list)
        assert isinstance(insight.prevention_signals, list)


def test_insights_sleep_flag_produces_sleep_insight() -> None:
    """sleep_duration_low flag must produce a sleep-kind Insight."""
    vitality_with_sleep = _make_vitality(risk_flags=["sleep_duration_low"])
    insights = derive_insights(
        vitality=vitality_with_sleep,
        ehr=[],
        lifestyle=None,
    )
    sleep_insights = [i for i in insights if i.kind == "sleep"]
    assert sleep_insights, "Expected a sleep Insight when sleep_duration_low flag is set"


def test_insights_activity_flag_produces_activity_insight() -> None:
    """activity_low flag must produce an activity-kind Insight."""
    vitality_with_activity = _make_vitality(risk_flags=["activity_low"])
    insights = derive_insights(
        vitality=vitality_with_activity,
        ehr=[],
        lifestyle=None,
    )
    activity_insights = [i for i in insights if i.kind == "activity"]
    assert activity_insights, "Expected an activity Insight when activity_low flag is set"


def test_insights_metabolic_flag_produces_metabolic_insight() -> None:
    """metabolic_hba1c_elevated flag must produce a metabolic-kind Insight."""
    vitality_with_metabolic = _make_vitality(risk_flags=["metabolic_hba1c_elevated"])
    insights = derive_insights(
        vitality=vitality_with_metabolic,
        ehr=[_lab_panel(hba1c_pct=6.1)],
        lifestyle=None,
    )
    metabolic_insights = [i for i in insights if i.kind == "metabolic"]
    assert metabolic_insights, "Expected a metabolic Insight when metabolic_hba1c_elevated flag is set"


def test_insight_disclaimer_matches_constant() -> None:
    """Every Insight carries the DISCLAIMER constant — locks the default value."""
    insights = derive_insights(
        vitality=_ANNA_VITALITY,
        ehr=[_ANNA_LAB],
        lifestyle=_ANNA_LIFESTYLE,
    )
    assert insights, "Expected at least one Insight for Anna to test disclaimer"
    for insight in insights:
        assert insight.disclaimer == DISCLAIMER, (
            f"Insight.disclaimer mismatch: expected {DISCLAIMER!r}, got {insight.disclaimer!r}"
        )
