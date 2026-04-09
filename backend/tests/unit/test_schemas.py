"""Unit tests for Pydantic v2 response schemas (DTOs).

Tests cover:
- Round-trip validation (model_validate -> model_dump) for each schema
- Wellness framing: no diagnostic verbs in field names
- Disclaimer defaults on score/insight schemas
- Slice 2: AI envelope, coach, records Q&A, protocol, survey, daily log,
  meal log, outlook, notifications, clinical review, referral, messages
"""

from __future__ import annotations

import datetime

import pytest
from pydantic import BaseModel, ValidationError

from app.schemas.appointments import AppointmentListOut, AppointmentOut
from app.schemas.gdpr import GDPRDeleteAck, GDPRExportOut
from app.schemas.insights import InsightOut, InsightsListOut
from app.schemas.patient import PatientProfileOut
from app.schemas.records import EHRRecordListOut, EHRRecordOut
from app.schemas.vitality import TrendPoint, VitalityOut
from app.schemas.wearable import WearableDayOut, WearableSeriesOut

# Slice 2 imports
from app.schemas.ai_common import AIMeta, AIResponseEnvelope
from app.schemas.coach import CoachChatRequest, CoachEvent
from app.schemas.records_qa import RecordsQARequest, Citation, RecordsQAResponse
from app.schemas.protocol import (
    GeneratedAction,
    GeneratedProtocol,
    ProtocolOut,
    ProtocolActionOut,
    CompleteActionRequest,
    CompleteActionResponse,
)
from app.schemas.survey import SurveyKind, SurveySubmitRequest, SurveyResponseOut, SurveyHistoryOut
from app.schemas.daily_log import DailyLogIn, DailyLogOut, DailyLogListOut
from app.schemas.meal_log import MealAnalysis, MealLogOut, MealLogListOut, MealLogUploadResponse
from app.schemas.outlook import (
    OutlookOut,
    OutlookNarratorRequest,
    OutlookNarratorResponse,
    FutureSelfRequest,
    FutureSelfResponse,
)
from app.schemas.notifications import SmartNotificationRequest, SmartNotificationResponse
from app.schemas.clinical_review import ClinicalReviewIn, ClinicalReviewOut
from app.schemas.referral import ReferralIn, ReferralOut
from app.schemas.messages import MessageIn, MessageOut, MessageListOut

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
    # Slice 2
    AIMeta,
    AIResponseEnvelope,
    CoachChatRequest,
    CoachEvent,
    RecordsQARequest,
    Citation,
    RecordsQAResponse,
    GeneratedAction,
    GeneratedProtocol,
    ProtocolOut,
    ProtocolActionOut,
    CompleteActionRequest,
    CompleteActionResponse,
    SurveySubmitRequest,
    SurveyResponseOut,
    SurveyHistoryOut,
    DailyLogIn,
    DailyLogOut,
    DailyLogListOut,
    MealAnalysis,
    MealLogOut,
    MealLogListOut,
    MealLogUploadResponse,
    OutlookOut,
    OutlookNarratorRequest,
    OutlookNarratorResponse,
    FutureSelfRequest,
    FutureSelfResponse,
    SmartNotificationRequest,
    SmartNotificationResponse,
    ClinicalReviewIn,
    ClinicalReviewOut,
    ReferralIn,
    ReferralOut,
    MessageIn,
    MessageOut,
    MessageListOut,
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
    with pytest.raises(ValidationError):
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
    with pytest.raises(ValidationError):
        GDPRDeleteAck.model_validate({"status": "deleted", "message": "..."})


# ===========================================================================
# Slice 2 — AI envelope schemas
# ===========================================================================


def test_ai_meta_round_trip() -> None:
    """AIMeta round-trips with all required fields."""
    data = {
        "model": "gemini-2.5-flash",
        "prompt_name": "coach",
        "request_id": "req-abc123",
        "token_in": 512,
        "token_out": 256,
        "latency_ms": 420,
    }
    obj = AIMeta.model_validate(data)
    result = obj.model_dump()
    assert result["model"] == "gemini-2.5-flash"
    assert result["prompt_name"] == "coach"
    assert result["request_id"] == "req-abc123"
    assert result["token_in"] == 512
    assert result["token_out"] == 256
    assert result["latency_ms"] == 420


def test_ai_meta_requires_all_fields() -> None:
    """AIMeta raises ValidationError when required fields are missing."""
    with pytest.raises(ValidationError):
        AIMeta.model_validate({"model": "gemini-2.5-flash"})


def test_ai_response_envelope_has_disclaimer_default() -> None:
    """AIResponseEnvelope.disclaimer has a non-empty default."""
    meta = AIMeta(
        model="gemini-2.5-flash",
        prompt_name="test",
        request_id="r1",
        token_in=1,
        token_out=1,
        latency_ms=1,
    )
    obj = AIResponseEnvelope(ai_meta=meta)
    assert "medical advice" in obj.disclaimer.lower() or "wellness" in obj.disclaimer.lower()


def test_ai_response_envelope_disclaimer_default_text() -> None:
    """AIResponseEnvelope.disclaimer defaults to the wellness framing string."""
    field = AIResponseEnvelope.model_fields["disclaimer"]
    assert field.default is not None
    assert len(str(field.default)) > 0


# ===========================================================================
# Slice 2 — Coach schemas
# ===========================================================================


def test_coach_chat_request_round_trip() -> None:
    """CoachChatRequest round-trips with message and history."""
    data = {
        "message": "How can I improve my sleep?",
        "history": [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi! How can I help?"},
        ],
    }
    obj = CoachChatRequest.model_validate(data)
    result = obj.model_dump()
    assert result["message"] == "How can I improve my sleep?"
    assert len(result["history"]) == 2


def test_coach_chat_request_empty_history() -> None:
    """CoachChatRequest accepts empty history list."""
    obj = CoachChatRequest.model_validate({"message": "Hello", "history": []})
    assert obj.message == "Hello"
    assert obj.history == []


def test_coach_event_token_type() -> None:
    """CoachEvent with type='token' round-trips."""
    data = {"type": "token", "payload": "Here is your advice"}
    obj = CoachEvent.model_validate(data)
    assert obj.type == "token"
    assert obj.payload == "Here is your advice"


def test_coach_event_done_type() -> None:
    """CoachEvent with type='done' round-trips."""
    data = {"type": "done", "payload": None}
    obj = CoachEvent.model_validate(data)
    assert obj.type == "done"


def test_coach_event_invalid_type() -> None:
    """CoachEvent rejects unknown type values."""
    with pytest.raises(ValidationError):
        CoachEvent.model_validate({"type": "unknown_type", "payload": "x"})


def test_coach_event_protocol_suggestion_type() -> None:
    """CoachEvent with type='protocol_suggestion' round-trips."""
    data = {"type": "protocol_suggestion", "payload": {"action": "run 30 min"}}
    obj = CoachEvent.model_validate(data)
    assert obj.type == "protocol_suggestion"


def test_coach_event_error_type() -> None:
    """CoachEvent with type='error' round-trips."""
    data = {"type": "error", "payload": "Something went wrong"}
    obj = CoachEvent.model_validate(data)
    assert obj.type == "error"


# ===========================================================================
# Slice 2 — Records Q&A schemas
# ===========================================================================


def test_records_qa_request_round_trip() -> None:
    """RecordsQARequest round-trips with a question."""
    obj = RecordsQARequest.model_validate({"question": "What is my LDL level?"})
    assert obj.question == "What is my LDL level?"


def test_records_qa_request_requires_question() -> None:
    """RecordsQARequest raises ValidationError when question is missing."""
    with pytest.raises(ValidationError):
        RecordsQARequest.model_validate({})


def test_citation_round_trip() -> None:
    """Citation round-trips with record_id and snippet."""
    data = {"record_id": 42, "snippet": "LDL cholesterol: 3.84 mmol/L"}
    obj = Citation.model_validate(data)
    result = obj.model_dump()
    assert result["record_id"] == 42
    assert result["snippet"] == "LDL cholesterol: 3.84 mmol/L"


def test_records_qa_response_has_envelope() -> None:
    """RecordsQAResponse carries disclaimer and ai_meta from AIResponseEnvelope."""
    meta = {
        "model": "gemini-2.5-pro",
        "prompt_name": "records-qa",
        "request_id": "r1",
        "token_in": 1000,
        "token_out": 200,
        "latency_ms": 800,
    }
    data = {
        "answer": "Your LDL was 3.84 mmol/L on 2024-01-15.",
        "citations": [{"record_id": 1, "snippet": "LDL: 3.84"}],
        "ai_meta": meta,
    }
    obj = RecordsQAResponse.model_validate(data)
    assert obj.answer == "Your LDL was 3.84 mmol/L on 2024-01-15."
    assert len(obj.citations) == 1
    assert "medical advice" in obj.disclaimer.lower() or "wellness" in obj.disclaimer.lower()
    assert obj.ai_meta.prompt_name == "records-qa"


def test_records_qa_response_empty_citations() -> None:
    """RecordsQAResponse accepts empty citations list."""
    meta = {
        "model": "gemini-2.5-pro",
        "prompt_name": "records-qa",
        "request_id": "r2",
        "token_in": 100,
        "token_out": 50,
        "latency_ms": 300,
    }
    obj = RecordsQAResponse.model_validate({"answer": "No records found.", "citations": [], "ai_meta": meta})
    assert obj.citations == []


# ===========================================================================
# Slice 2 — Protocol schemas
# ===========================================================================


def test_generated_action_round_trip() -> None:
    """GeneratedAction round-trips with all required fields."""
    data = {
        "category": "movement",
        "title": "30-minute brisk walk",
        "target": "30 minutes daily",
        "rationale": "Improves cardiovascular health and longevity.",
        "dimension": "cardio_fitness",
    }
    obj = GeneratedAction.model_validate(data)
    result = obj.model_dump()
    assert result["category"] == "movement"
    assert result["dimension"] == "cardio_fitness"


def test_generated_action_invalid_category() -> None:
    """GeneratedAction rejects invalid category values."""
    with pytest.raises(ValidationError):
        GeneratedAction.model_validate(
            {
                "category": "yoga",  # invalid
                "title": "Yoga session",
                "target": "daily",
                "rationale": "Relaxing.",
                "dimension": "lifestyle_behavioral",
            }
        )


def test_generated_action_invalid_dimension() -> None:
    """GeneratedAction rejects invalid dimension values."""
    with pytest.raises(ValidationError):
        GeneratedAction.model_validate(
            {
                "category": "sleep",
                "title": "Go to bed early",
                "target": "10pm",
                "rationale": "Better sleep.",
                "dimension": "mental_health",  # invalid
            }
        )


def test_generated_protocol_round_trip() -> None:
    """GeneratedProtocol round-trips with rationale and 3–7 actions."""
    action = {
        "category": "sleep",
        "title": "Consistent sleep schedule",
        "target": "10pm bedtime",
        "rationale": "Stabilises circadian rhythm.",
        "dimension": "sleep_recovery",
    }
    data = {
        "rationale": "Focus on sleep consistency to improve your score this week.",
        "actions": [action, action, action],
    }
    obj = GeneratedProtocol.model_validate(data)
    assert obj.rationale.startswith("Focus")
    assert len(obj.actions) == 3


def test_protocol_out_round_trip() -> None:
    """ProtocolOut round-trips with id, patient_id, generated_at, rationale, actions."""
    data = {
        "id": 1,
        "patient_id": "PT0001",
        "generated_at": "2024-01-15T08:00:00",
        "rationale": "Your protocol this week.",
        "actions": [],
    }
    obj = ProtocolOut.model_validate(data)
    result = obj.model_dump()
    assert result["id"] == 1
    assert result["patient_id"] == "PT0001"
    assert result["actions"] == []


def test_protocol_action_out_round_trip() -> None:
    """ProtocolActionOut round-trips with completion tracking fields."""
    data = {
        "id": 10,
        "protocol_id": 1,
        "category": "nutrition",
        "title": "Add a handful of nuts",
        "target": "daily snack",
        "rationale": "Rich in healthy fats.",
        "dimension": "biological_age",
        "completed_today": False,
        "streak_days": 0,
    }
    obj = ProtocolActionOut.model_validate(data)
    assert obj.completed_today is False
    assert obj.streak_days == 0


def test_complete_action_request_round_trip() -> None:
    """CompleteActionRequest round-trips with action_id."""
    obj = CompleteActionRequest.model_validate({"action_id": 42})
    assert obj.action_id == 42


def test_complete_action_response_round_trip() -> None:
    """CompleteActionResponse round-trips with streak_days and completed_at."""
    data = {
        "action_id": 42,
        "streak_days": 5,
        "completed_at": "2024-01-15T10:00:00",
    }
    obj = CompleteActionResponse.model_validate(data)
    assert obj.streak_days == 5


# ===========================================================================
# Slice 2 — Survey schemas
# ===========================================================================


def test_survey_kind_enum_values() -> None:
    """SurveyKind enum has onboarding, weekly, quarterly values."""
    assert SurveyKind.onboarding == "onboarding"
    assert SurveyKind.weekly == "weekly"
    assert SurveyKind.quarterly == "quarterly"


def test_survey_submit_request_round_trip() -> None:
    """SurveySubmitRequest round-trips with kind and answers."""
    data = {
        "kind": "onboarding",
        "answers": {"diet_quality_score": 7, "stress_level": 4},
    }
    obj = SurveySubmitRequest.model_validate(data)
    assert obj.kind == SurveyKind.onboarding
    assert obj.answers["diet_quality_score"] == 7


def test_survey_submit_request_invalid_kind() -> None:
    """SurveySubmitRequest rejects unknown kind values."""
    with pytest.raises(ValidationError):
        SurveySubmitRequest.model_validate({"kind": "annual", "answers": {}})


def test_survey_response_out_round_trip() -> None:
    """SurveyResponseOut round-trips with id, patient_id, kind, submitted_at, answers."""
    data = {
        "id": 1,
        "patient_id": "PT0001",
        "kind": "weekly",
        "submitted_at": "2024-01-15T12:00:00",
        "answers": {"sleep_satisfaction": 7},
    }
    obj = SurveyResponseOut.model_validate(data)
    result = obj.model_dump()
    assert result["kind"] == "weekly"
    assert result["answers"]["sleep_satisfaction"] == 7


def test_survey_history_out_round_trip() -> None:
    """SurveyHistoryOut wraps a list of SurveyResponseOut."""
    data = {
        "patient_id": "PT0001",
        "responses": [],
    }
    obj = SurveyHistoryOut.model_validate(data)
    assert obj.patient_id == "PT0001"
    assert obj.responses == []


# ===========================================================================
# Slice 2 — DailyLog schemas
# ===========================================================================


def test_daily_log_in_round_trip() -> None:
    """DailyLogIn round-trips with mood, workout, sleep, water, alcohol."""
    data = {
        "date": "2024-01-15",
        "mood_score": 7,
        "workout_minutes": 45,
        "sleep_hours": 7.5,
        "water_glasses": 8,
        "alcohol_units": 0,
    }
    obj = DailyLogIn.model_validate(data)
    result = obj.model_dump()
    assert result["mood_score"] == 7
    assert result["sleep_hours"] == pytest.approx(7.5)


def test_daily_log_in_optional_fields() -> None:
    """DailyLogIn accepts None for all optional metric fields."""
    obj = DailyLogIn.model_validate({"date": "2024-01-15"})
    assert obj.mood_score is None
    assert obj.workout_minutes is None


def test_daily_log_out_round_trip() -> None:
    """DailyLogOut round-trips with id, patient_id, all fields."""
    data = {
        "id": 1,
        "patient_id": "PT0001",
        "date": "2024-01-15",
        "mood_score": 7,
        "workout_minutes": 45,
        "sleep_hours": 7.5,
        "water_glasses": 8,
        "alcohol_units": 0,
        "logged_at": "2024-01-15T20:00:00",
    }
    obj = DailyLogOut.model_validate(data)
    assert obj.id == 1
    assert obj.patient_id == "PT0001"


def test_daily_log_list_out_round_trip() -> None:
    """DailyLogListOut wraps a list of DailyLogOut."""
    data = {"patient_id": "PT0001", "logs": []}
    obj = DailyLogListOut.model_validate(data)
    assert obj.patient_id == "PT0001"
    assert obj.logs == []


# ===========================================================================
# Slice 2 — MealLog schemas
# ===========================================================================


def test_meal_analysis_round_trip() -> None:
    """MealAnalysis round-trips with classification, macros, longevity_swap."""
    data = {
        "classification": "grilled salmon, white rice, broccoli",
        "macros": {"kcal": 650, "protein_g": 42.0, "carbs_g": 58.0, "fat_g": 18.0},
        "longevity_swap": "Replace white rice with brown rice for more fibre.",
    }
    obj = MealAnalysis.model_validate(data)
    result = obj.model_dump()
    assert result["classification"] == "grilled salmon, white rice, broccoli"
    assert result["macros"]["protein_g"] == pytest.approx(42.0)
    assert result["longevity_swap"] == "Replace white rice with brown rice for more fibre."


def test_meal_analysis_empty_swap() -> None:
    """MealAnalysis accepts empty string for longevity_swap (already optimal)."""
    data = {
        "classification": "grilled salmon",
        "macros": {"kcal": 300, "protein_g": 35.0, "carbs_g": 0.0, "fat_g": 15.0},
        "longevity_swap": "",
    }
    obj = MealAnalysis.model_validate(data)
    assert obj.longevity_swap == ""


def test_meal_log_upload_response_has_envelope() -> None:
    """MealLogUploadResponse carries disclaimer and ai_meta."""
    meta = {
        "model": "gemini-2.5-flash",
        "prompt_name": "meal-vision",
        "request_id": "r3",
        "token_in": 200,
        "token_out": 100,
        "latency_ms": 350,
    }
    data = {
        "meal_log_id": 7,
        "photo_uri": "local://var/photos/PT0001/abc.jpg",
        "analysis": {
            "classification": "oatmeal",
            "macros": {"kcal": 380, "protein_g": 10.0, "carbs_g": 65.0, "fat_g": 7.0},
            "longevity_swap": "",
        },
        "ai_meta": meta,
    }
    obj = MealLogUploadResponse.model_validate(data)
    assert obj.meal_log_id == 7
    assert "medical advice" in obj.disclaimer.lower() or "wellness" in obj.disclaimer.lower()


def test_meal_log_out_round_trip() -> None:
    """MealLogOut round-trips with id, patient_id, analysis, logged_at."""
    data = {
        "id": 3,
        "patient_id": "PT0001",
        "logged_at": "2024-01-15T12:30:00",
        "photo_uri": "local://var/photos/PT0001/abc.jpg",
        "analysis": {
            "classification": "salad",
            "macros": {"kcal": 250, "protein_g": 8.0, "carbs_g": 30.0, "fat_g": 12.0},
            "longevity_swap": "Add legumes for more protein.",
        },
        "notes": "Lunch",
    }
    obj = MealLogOut.model_validate(data)
    assert obj.id == 3
    assert obj.notes == "Lunch"


def test_meal_log_list_out_round_trip() -> None:
    """MealLogListOut wraps a list of MealLogOut."""
    data = {"patient_id": "PT0001", "logs": []}
    obj = MealLogListOut.model_validate(data)
    assert obj.logs == []


# ===========================================================================
# Slice 2 — Outlook schemas
# ===========================================================================


def test_outlook_out_round_trip() -> None:
    """OutlookOut round-trips with horizon_months, projected_score, narrative."""
    data = {
        "horizon_months": 6,
        "projected_score": 74.5,
        "narrative": "Hold your streak and your Outlook reaches 74 by October.",
        "computed_at": "2024-01-15T12:00:00",
    }
    obj = OutlookOut.model_validate(data)
    result = obj.model_dump()
    assert result["horizon_months"] == 6
    assert result["projected_score"] == pytest.approx(74.5)


def test_outlook_narrator_request_round_trip() -> None:
    """OutlookNarratorRequest round-trips with driver context."""
    data = {
        "patient_id": "PT0001",
        "horizon_months": 6,
        "top_drivers": ["sleep", "cardio"],
    }
    obj = OutlookNarratorRequest.model_validate(data)
    assert obj.patient_id == "PT0001"
    assert len(obj.top_drivers) == 2


def test_outlook_narrator_response_has_envelope() -> None:
    """OutlookNarratorResponse carries disclaimer and ai_meta."""
    meta = {
        "model": "gemini-2.5-flash",
        "prompt_name": "outlook-narrator",
        "request_id": "r4",
        "token_in": 150,
        "token_out": 50,
        "latency_ms": 200,
    }
    data = {
        "narrative": "Keep your sleep streak for an October milestone.",
        "ai_meta": meta,
    }
    obj = OutlookNarratorResponse.model_validate(data)
    assert obj.narrative.startswith("Keep")
    assert "medical advice" in obj.disclaimer.lower() or "wellness" in obj.disclaimer.lower()


def test_future_self_request_round_trip() -> None:
    """FutureSelfRequest round-trips with slider values."""
    data = {
        "patient_id": "PT0001",
        "sliders": {"sleep_improvement": 2, "exercise_frequency": 4},
    }
    obj = FutureSelfRequest.model_validate(data)
    assert obj.sliders["sleep_improvement"] == 2


def test_future_self_response_has_envelope() -> None:
    """FutureSelfResponse carries bio_age, narrative, disclaimer, ai_meta."""
    meta = {
        "model": "gemini-2.5-flash",
        "prompt_name": "future-self",
        "request_id": "r5",
        "token_in": 300,
        "token_out": 180,
        "latency_ms": 450,
    }
    data = {
        "bio_age": 38,
        "narrative": "At 70 on current trajectory you feel vibrant and active.",
        "ai_meta": meta,
    }
    obj = FutureSelfResponse.model_validate(data)
    assert obj.bio_age == 38
    assert "medical advice" in obj.disclaimer.lower() or "wellness" in obj.disclaimer.lower()


# ===========================================================================
# Slice 2 — Notifications schemas
# ===========================================================================


def test_smart_notification_request_round_trip() -> None:
    """SmartNotificationRequest round-trips with trigger_kind and context."""
    data = {
        "trigger_kind": "streak_at_risk",
        "context": {"streak_days": 6, "last_action": "movement"},
    }
    obj = SmartNotificationRequest.model_validate(data)
    assert obj.trigger_kind == "streak_at_risk"


def test_smart_notification_response_has_envelope() -> None:
    """SmartNotificationResponse carries title, body, cta, disclaimer, ai_meta."""
    meta = {
        "model": "gemini-2.5-flash",
        "prompt_name": "notifications",
        "request_id": "r6",
        "token_in": 80,
        "token_out": 40,
        "latency_ms": 120,
    }
    data = {
        "title": "Keep your streak alive!",
        "body": "You are 1 day away from a 7-day streak. Go for a 20-min walk today.",
        "cta": "Log activity",
        "ai_meta": meta,
    }
    obj = SmartNotificationResponse.model_validate(data)
    assert obj.title == "Keep your streak alive!"
    assert obj.cta == "Log activity"
    assert "medical advice" in obj.disclaimer.lower() or "wellness" in obj.disclaimer.lower()


# ===========================================================================
# Slice 2 — ClinicalReview schemas
# ===========================================================================


def test_clinical_review_in_round_trip() -> None:
    """ClinicalReviewIn round-trips with patient_id and notes."""
    data = {
        "patient_id": "PT0001",
        "notes": "Patient reports persistent fatigue.",
    }
    obj = ClinicalReviewIn.model_validate(data)
    assert obj.patient_id == "PT0001"
    assert "fatigue" in obj.notes


def test_clinical_review_out_round_trip() -> None:
    """ClinicalReviewOut round-trips with id, patient_id, status, created_at."""
    data = {
        "id": 1,
        "patient_id": "PT0001",
        "notes": "Flagged for review.",
        "status": "pending",
        "created_at": "2024-01-15T09:00:00",
    }
    obj = ClinicalReviewOut.model_validate(data)
    assert obj.status == "pending"


# ===========================================================================
# Slice 2 — Referral schemas
# ===========================================================================


def test_referral_in_round_trip() -> None:
    """ReferralIn round-trips with patient_id, specialty, reason."""
    data = {
        "patient_id": "PT0001",
        "specialty": "cardiology",
        "reason": "Elevated LDL and HRV variability — please review.",
    }
    obj = ReferralIn.model_validate(data)
    assert obj.specialty == "cardiology"


def test_referral_out_round_trip() -> None:
    """ReferralOut round-trips with id, patient_id, specialty, created_at."""
    data = {
        "id": 1,
        "patient_id": "PT0001",
        "specialty": "cardiology",
        "reason": "Elevated LDL.",
        "status": "pending",
        "created_at": "2024-01-15T10:00:00",
    }
    obj = ReferralOut.model_validate(data)
    assert obj.id == 1
    assert obj.status == "pending"


# ===========================================================================
# Slice 2 — Messages schemas
# ===========================================================================


def test_message_in_round_trip() -> None:
    """MessageIn round-trips with patient_id and content."""
    data = {
        "patient_id": "PT0001",
        "content": "I have a question about my protocol.",
    }
    obj = MessageIn.model_validate(data)
    assert obj.content == "I have a question about my protocol."


def test_message_out_round_trip() -> None:
    """MessageOut round-trips with id, patient_id, content, sent_at, direction."""
    data = {
        "id": 1,
        "patient_id": "PT0001",
        "content": "Welcome to Longevity+",
        "sent_at": "2024-01-15T08:00:00",
        "direction": "outbound",
    }
    obj = MessageOut.model_validate(data)
    assert obj.direction == "outbound"


def test_message_out_invalid_direction() -> None:
    """MessageOut rejects direction values other than 'inbound' or 'outbound'."""
    with pytest.raises(ValidationError):
        MessageOut.model_validate(
            {
                "id": 1,
                "patient_id": "PT0001",
                "content": "Hello",
                "sent_at": "2024-01-15T08:00:00",
                "direction": "sideways",  # invalid
            }
        )


def test_message_list_out_round_trip() -> None:
    """MessageListOut wraps a list of MessageOut."""
    data = {"patient_id": "PT0001", "messages": []}
    obj = MessageListOut.model_validate(data)
    assert obj.patient_id == "PT0001"
    assert obj.messages == []
