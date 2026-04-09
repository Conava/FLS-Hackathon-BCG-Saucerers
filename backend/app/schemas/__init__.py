"""Pydantic v2 response schemas (DTOs) for the Longevity+ API.

All schemas are BaseModel subclasses with ``ConfigDict(from_attributes=True)``
so they can be constructed from ORM model instances (SQLModel / SQLAlchemy).

Wellness framing invariant: no field name in any schema may contain the words
``diagnose``, ``diagnosis``, ``treat``, ``cure``, or ``prevent_disease``.
This is enforced by the ``test_no_diagnostic_verbs_in_field_names`` test.
"""

# Slice 1 — existing schemas
# Slice 2 — AI-layer and new domain schemas
from app.schemas.ai_common import AIMeta, AIResponseEnvelope
from app.schemas.appointments import AppointmentListOut, AppointmentOut
from app.schemas.clinical_review import ClinicalReviewIn, ClinicalReviewOut
from app.schemas.coach import CoachChatRequest, CoachEvent
from app.schemas.daily_log import DailyLogIn, DailyLogListOut, DailyLogOut
from app.schemas.gdpr import GDPRDeleteAck, GDPRExportOut
from app.schemas.insights import InsightOut, InsightsListOut
from app.schemas.meal_log import (
    MealAnalysis,
    MealLogListOut,
    MealLogOut,
    MealLogUploadResponse,
)
from app.schemas.messages import MessageIn, MessageListOut, MessageOut
from app.schemas.notifications import SmartNotificationRequest, SmartNotificationResponse
from app.schemas.outlook import (
    FutureSelfRequest,
    FutureSelfResponse,
    OutlookNarratorRequest,
    OutlookNarratorResponse,
    OutlookOut,
)
from app.schemas.patient import PatientProfileOut
from app.schemas.protocol import (
    CompleteActionRequest,
    CompleteActionResponse,
    GeneratedAction,
    GeneratedProtocol,
    ProtocolActionOut,
    ProtocolOut,
)
from app.schemas.records import EHRRecordListOut, EHRRecordOut
from app.schemas.records_qa import Citation, RecordsQARequest, RecordsQAResponse
from app.schemas.referral import ReferralIn, ReferralOut
from app.schemas.survey import SurveyHistoryOut, SurveyKind, SurveyResponseOut, SurveySubmitRequest
from app.schemas.vitality import TrendPoint, VitalityOut
from app.schemas.wearable import WearableDayOut, WearableSeriesOut

__all__ = [
    # Slice 1
    "AppointmentListOut",
    "AppointmentOut",
    "EHRRecordListOut",
    "EHRRecordOut",
    "GDPRDeleteAck",
    "GDPRExportOut",
    "InsightOut",
    "InsightsListOut",
    "PatientProfileOut",
    "TrendPoint",
    "VitalityOut",
    "WearableDayOut",
    "WearableSeriesOut",
    # Slice 2 — AI envelope
    "AIMeta",
    "AIResponseEnvelope",
    # Slice 2 — Coach
    "CoachChatRequest",
    "CoachEvent",
    # Slice 2 — Records Q&A
    "Citation",
    "RecordsQARequest",
    "RecordsQAResponse",
    # Slice 2 — Protocol
    "CompleteActionRequest",
    "CompleteActionResponse",
    "GeneratedAction",
    "GeneratedProtocol",
    "ProtocolActionOut",
    "ProtocolOut",
    # Slice 2 — Survey
    "SurveyHistoryOut",
    "SurveyKind",
    "SurveyResponseOut",
    "SurveySubmitRequest",
    # Slice 2 — Daily log
    "DailyLogIn",
    "DailyLogListOut",
    "DailyLogOut",
    # Slice 2 — Meal log
    "MealAnalysis",
    "MealLogListOut",
    "MealLogOut",
    "MealLogUploadResponse",
    # Slice 2 — Outlook / insights AI
    "FutureSelfRequest",
    "FutureSelfResponse",
    "OutlookNarratorRequest",
    "OutlookNarratorResponse",
    "OutlookOut",
    # Slice 2 — Notifications
    "SmartNotificationRequest",
    "SmartNotificationResponse",
    # Slice 2 — Clinical review
    "ClinicalReviewIn",
    "ClinicalReviewOut",
    # Slice 2 — Referral
    "ReferralIn",
    "ReferralOut",
    # Slice 2 — Messages
    "MessageIn",
    "MessageListOut",
    "MessageOut",
]
