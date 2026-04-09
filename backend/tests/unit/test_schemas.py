"""Unit tests for Pydantic v2 response schemas (DTOs).

Tests cover:
- Round-trip validation (model_validate -> model_dump) for each schema
- Wellness framing: no diagnostic verbs in field names
- Disclaimer defaults on score/insight schemas
"""

from __future__ import annotations

import datetime
from typing import get_type_hints

import pytest
from pydantic import BaseModel

from app.schemas.appointments import AppointmentListOut, AppointmentOut
from app.schemas.gdpr import GDPRDeleteAck, GDPRExportOut
from app.schemas.insights import InsightOut, InsightsListOut
from app.schemas.patient import PatientProfileOut
from app.schemas.records import EHRRecordListOut, EHRRecordOut
from app.schemas.vitality import TrendPoint, VitalityOut
from app.schemas.wearable import WearableDayOut, WearableSeriesOut

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FORBIDDEN_VERBS = {"diagnose", "diagnosis", "treat", "cure", "prevent_disease"}

ALL_SCHEMA_CLASSES: list[type[BaseModel]] = [
    PatientProfileOut,
    EHRRecordOut,
    EHRRecordListOut,
    WearableDayOut,
    WearableSeriesOut,
    TrendPoint,
    VitalityOut,
    InsightOut,
    InsightsListOut,
    AppointmentOut,
    AppointmentListOut,
    GDPRExportOut,
    GDPRDeleteAck,
]


# ---------------------------------------------------------------------------
# Wellness framing guard
# ---------------------------------------------------------------------------


def test_no_diagnostic_verbs_in_field_names() -> None:
    """No field name in any schema may contain a diagnostic/treatment verb."""
    violations: list[str] = []
    for cls in ALL_SCHEMA_CLASSES:
        for field_name in cls.model_fields:
            for verb in FORBIDDEN_VERBS:
                if verb in field_name.lower():
                    violations.append(f"{cls.__name__}.{field_name} contains '{verb}'")
    assert violations == [], "Diagnostic verbs found in field names:\n" + "\n".join(violations)


# ---------------------------------------------------------------------------
# Disclaimer default
# ---------------------------------------------------------------------------


def test_disclaimer_default_set_vitality() -> None:
    """VitalityOut.disclaimer has a non-empty default value."""
    field = VitalityOut.model_fields["disclaimer"]
    assert field.default is not None
    assert "medical advice" in str(field.default).lower() or "wellness" in str(field.default).lower()


def test_disclaimer_default_set_insight() -> None:
    """InsightOut.disclaimer has a non-empty default value."""
    field = InsightOut.model_fields["disclaimer"]
    assert field.default is not None
    assert "medical advice" in str(field.default).lower() or "wellness" in str(field.default).lower()


# ---------------------------------------------------------------------------
# PatientProfileOut
# ---------------------------------------------------------------------------


def test_patient_profile_round_trip() -> None:
    """PatientProfileOut round-trips via model_validate and model_dump."""
    data = {
        "patient_id": "PT0282",
        "name": "Anna Weber",
        "age": 45,
        "country": "Germany",
        "sex": "female",
        "bmi": 24.5,
        "smoking_status": "never",
        "height_cm": 168.0,
        "weight_kg": 69.2,
    }
    obj = PatientProfileOut.model_validate(data)
    result = obj.model_dump()
    assert result["patient_id"] == "PT0282"
    assert result["name"] == "Anna Weber"
    assert result["age"] == 45
    assert result["country"] == "Germany"
    assert result["bmi"] == pytest.approx(24.5)


def test_patient_profile_optional_fields_none() -> None:
    """PatientProfileOut accepts None for optional fields."""
    data = {
        "patient_id": "PT0001",
        "name": "Unknown",
        "age": 30,
        "country": "DE",
        "sex": None,
        "bmi": None,
        "smoking_status": None,
        "height_cm": None,
        "weight_kg": None,
    }
    obj = PatientProfileOut.model_validate(data)
    assert obj.bmi is None
    assert obj.height_cm is None


# ---------------------------------------------------------------------------
# EHRRecordOut / EHRRecordListOut
# ---------------------------------------------------------------------------


def test_ehr_record_out_round_trip() -> None:
    """EHRRecordOut round-trips with arbitrary payload."""
    data = {
        "id": 1,
        "record_type": "lab_panel",
        "recorded_at": "2024-01-15T10:00:00",
        "payload": {"total_cholesterol_mmol": 7.05, "ldl_mmol": 3.84},
        "source": "csv",
    }
    obj = EHRRecordOut.model_validate(data)
    result = obj.model_dump()
    assert result["id"] == 1
    assert result["record_type"] == "lab_panel"
    assert result["payload"]["ldl_mmol"] == pytest.approx(3.84)
    assert result["source"] == "csv"


def test_ehr_record_list_out_round_trip() -> None:
    """EHRRecordListOut wraps a list of records."""
    record_data = {
        "id": 2,
        "record_type": "condition",
        "recorded_at": "2023-06-01T00:00:00",
        "payload": {"name": "Hypertension", "icd10": "I10"},
        "source": "csv",
    }
    data = {
        "patient_id": "PT0282",
        "records": [record_data],
        "total": 1,
    }
    obj = EHRRecordListOut.model_validate(data)
    result = obj.model_dump()
    assert result["total"] == 1
    assert len(result["records"]) == 1
    assert result["records"][0]["record_type"] == "condition"


# ---------------------------------------------------------------------------
# WearableDayOut / WearableSeriesOut
# ---------------------------------------------------------------------------


def test_wearable_day_out_round_trip() -> None:
    """WearableDayOut round-trips with all wearable columns."""
    data = {
        "patient_id": "PT0282",
        "date": "2024-01-15",
        "resting_hr_bpm": 62,
        "hrv_rmssd_ms": 45.2,
        "steps": 9500,
        "active_minutes": 42,
        "sleep_duration_hrs": 7.5,
        "sleep_quality_score": 80,
        "deep_sleep_pct": 22.0,
        "spo2_avg_pct": 98.5,
        "calories_burned_kcal": 1850,
    }
    obj = WearableDayOut.model_validate(data)
    result = obj.model_dump()
    assert result["steps"] == 9500
    assert result["sleep_duration_hrs"] == pytest.approx(7.5)


def test_wearable_series_out_round_trip() -> None:
    """WearableSeriesOut wraps a list of WearableDayOut."""
    day_data = {
        "patient_id": "PT0282",
        "date": "2024-01-15",
        "resting_hr_bpm": 62,
        "hrv_rmssd_ms": 45.2,
        "steps": 9500,
        "active_minutes": 42,
        "sleep_duration_hrs": 7.5,
        "sleep_quality_score": 80,
        "deep_sleep_pct": 22.0,
        "spo2_avg_pct": 98.5,
        "calories_burned_kcal": 1850,
    }
    data = {"patient_id": "PT0282", "days": [day_data]}
    obj = WearableSeriesOut.model_validate(data)
    result = obj.model_dump()
    assert result["patient_id"] == "PT0282"
    assert len(result["days"]) == 1
    assert result["days"][0]["steps"] == 9500


# ---------------------------------------------------------------------------
# TrendPoint / VitalityOut
# ---------------------------------------------------------------------------


def test_trend_point_round_trip() -> None:
    """TrendPoint round-trips with date and score."""
    data = {"date": "2024-01-15", "score": 72.5}
    obj = TrendPoint.model_validate(data)
    result = obj.model_dump()
    assert result["score"] == pytest.approx(72.5)


def test_vitality_out_round_trip() -> None:
    """VitalityOut round-trips with score, subscores, trend, risk_flags, and disclaimer."""
    trend = [{"date": f"2024-01-{i:02d}", "score": 60.0 + i} for i in range(1, 8)]
    data = {
        "score": 68.0,
        "subscores": {
            "sleep": 70.0,
            "activity": 65.0,
            "metabolic": 55.0,
            "cardio": 72.0,
            "lifestyle": 78.0,
        },
        "trend": trend,
        "computed_at": "2024-01-15T12:00:00",
        "risk_flags": ["elevated_ldl"],
    }
    obj = VitalityOut.model_validate(data)
    result = obj.model_dump()
    assert result["score"] == pytest.approx(68.0)
    assert set(result["subscores"].keys()) == {"sleep", "activity", "metabolic", "cardio", "lifestyle"}
    assert len(result["trend"]) == 7
    assert result["disclaimer"] == "Wellness signal, not medical advice."
    assert "elevated_ldl" in result["risk_flags"]


def test_vitality_out_disclaimer_is_default() -> None:
    """VitalityOut.disclaimer does not need to be supplied — it has a default."""
    trend = [{"date": "2024-01-15", "score": 70.0}]
    obj = VitalityOut(
        score=70.0,
        subscores={"sleep": 70.0, "activity": 70.0, "metabolic": 70.0, "cardio": 70.0, "lifestyle": 70.0},
        trend=[TrendPoint(date=datetime.date(2024, 1, 15), score=70.0)],
        computed_at=datetime.datetime(2024, 1, 15, 12, 0),
        risk_flags=[],
    )
    assert obj.disclaimer == "Wellness signal, not medical advice."


# ---------------------------------------------------------------------------
# InsightOut / InsightsListOut
# ---------------------------------------------------------------------------


def test_insight_out_round_trip() -> None:
    """InsightOut round-trips with all fields including signals."""
    data = {
        "kind": "lipid",
        "severity": "moderate",
        "message": "Your LDL cholesterol level is elevated. Consider dietary changes.",
        "signals": ["LDL 3.84 mmol/L (above 3.0 threshold)"],
        "prevention_signals": ["Increase omega-3 intake", "Reduce saturated fat"],
    }
    obj = InsightOut.model_validate(data)
    result = obj.model_dump()
    assert result["kind"] == "lipid"
    assert result["severity"] == "moderate"
    assert result["disclaimer"] == "Wellness signal, not medical advice."
    assert len(result["signals"]) == 1
    assert len(result["prevention_signals"]) == 2


def test_insight_out_severity_validation() -> None:
    """InsightOut.severity only accepts 'low', 'moderate', 'high'."""
    with pytest.raises(Exception):
        InsightOut.model_validate(
            {
                "kind": "test",
                "severity": "critical",  # invalid
                "message": "test",
                "signals": [],
                "prevention_signals": [],
            }
        )


def test_insights_list_out_round_trip() -> None:
    """InsightsListOut wraps a list of InsightOut and exposes top-level fields."""
    insight_data = {
        "kind": "sleep",
        "severity": "low",
        "message": "Sleep quality is slightly below optimal.",
        "signals": ["avg 6.5 hrs vs 7+ recommended"],
        "prevention_signals": ["Maintain consistent sleep schedule"],
    }
    data = {
        "patient_id": "PT0282",
        "insights": [insight_data],
        "risk_flags": ["poor_sleep"],
        "signals": ["avg 6.5 hrs vs 7+ recommended"],
        "prevention_signals": ["Maintain consistent sleep schedule"],
    }
    obj = InsightsListOut.model_validate(data)
    result = obj.model_dump()
    assert result["patient_id"] == "PT0282"
    assert len(result["insights"]) == 1
    assert "poor_sleep" in result["risk_flags"]


# ---------------------------------------------------------------------------
# AppointmentOut / AppointmentListOut
# ---------------------------------------------------------------------------


def test_appointment_out_round_trip() -> None:
    """AppointmentOut round-trips with all fields including optional price."""
    data = {
        "id": "appt-001",
        "title": "Lipid Panel Follow-up",
        "provider": "Dr. Müller",
        "location": "Cardio Wellness Hamburg",
        "starts_at": "2024-02-10T09:30:00",
        "duration_minutes": 30,
        "price_eur": 89.0,
        "covered_percent": 80,
    }
    obj = AppointmentOut.model_validate(data)
    result = obj.model_dump()
    assert result["id"] == "appt-001"
    assert result["price_eur"] == pytest.approx(89.0)
    assert result["covered_percent"] == 80


def test_appointment_out_optional_price_none() -> None:
    """AppointmentOut accepts None for price_eur and covered_percent."""
    data = {
        "id": "appt-002",
        "title": "Annual Check-up",
        "provider": "GP Practice",
        "location": "Online",
        "starts_at": "2024-02-20T14:00:00",
        "duration_minutes": 20,
        "price_eur": None,
        "covered_percent": None,
    }
    obj = AppointmentOut.model_validate(data)
    assert obj.price_eur is None
    assert obj.covered_percent is None


def test_appointment_list_out_round_trip() -> None:
    """AppointmentListOut wraps a list of AppointmentOut."""
    appt_data = {
        "id": "appt-001",
        "title": "Lipid Panel Follow-up",
        "provider": "Dr. Müller",
        "location": "Cardio Wellness Hamburg",
        "starts_at": "2024-02-10T09:30:00",
        "duration_minutes": 30,
        "price_eur": 89.0,
        "covered_percent": 80,
    }
    data = {"patient_id": "PT0282", "appointments": [appt_data]}
    obj = AppointmentListOut.model_validate(data)
    result = obj.model_dump()
    assert result["patient_id"] == "PT0282"
    assert len(result["appointments"]) == 1


# ---------------------------------------------------------------------------
# GDPRExportOut / GDPRDeleteAck
# ---------------------------------------------------------------------------


def test_gdpr_export_out_round_trip() -> None:
    """GDPRExportOut bundles patient, records, wearable, lifestyle."""
    data = {
        "patient_id": "PT0282",
        "patient": {"patient_id": "PT0282", "name": "Anna Weber", "age": 45, "country": "DE",
                    "sex": "female", "bmi": 24.5, "smoking_status": "never",
                    "height_cm": 168.0, "weight_kg": 69.2},
        "records": [],
        "wearable": [],
        "lifestyle": None,
        "exported_at": "2024-01-15T12:00:00",
    }
    obj = GDPRExportOut.model_validate(data)
    result = obj.model_dump()
    assert result["patient_id"] == "PT0282"
    assert result["records"] == []
    assert result["lifestyle"] is None


def test_gdpr_delete_ack_round_trip() -> None:
    """GDPRDeleteAck has status='scheduled' and a message."""
    data = {"status": "scheduled", "message": "Your wellness data will be removed within 30 days."}
    obj = GDPRDeleteAck.model_validate(data)
    result = obj.model_dump()
    assert result["status"] == "scheduled"
    assert "wellness" in result["message"].lower() or len(result["message"]) > 0


def test_gdpr_delete_ack_status_is_literal() -> None:
    """GDPRDeleteAck.status only accepts 'scheduled'."""
    with pytest.raises(Exception):
        GDPRDeleteAck.model_validate({"status": "deleted", "message": "..."})
