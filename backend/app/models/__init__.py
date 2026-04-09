"""SQLModel table entities for the Longevity+ Unified Patient Profile.

Import from here for a clean API:
    from app.models import Patient, EHRRecord, WearableDay, LifestyleProfile, VitalitySnapshot
    from app.models import Protocol, ProtocolAction, DailyLog, MealLog
    from app.models import SurveyResponse, VitalityOutlook, Message, Notification
    from app.models import ClinicalReview, Referral

All models are imported here to ensure SQLModel metadata is populated before
create_all() is called (SQLModel discovers tables at import time).
"""

# Slice 1 models
# Slice 2 models
from app.models.clinical_review import ClinicalReview
from app.models.daily_log import DailyLog
from app.models.ehr_record import EHRRecord, EHRRecordType
from app.models.lifestyle_profile import LifestyleProfile
from app.models.meal_log import MealLog
from app.models.message import Message
from app.models.notification import Notification
from app.models.patient import Patient
from app.models.protocol import Protocol, ProtocolAction
from app.models.referral import Referral
from app.models.survey_response import SurveyResponse
from app.models.vitality_outlook import VitalityOutlook
from app.models.vitality_snapshot import VitalitySnapshot
from app.models.wearable_day import WearableDay

__all__ = [
    # Slice 1
    "Patient",
    "EHRRecord",
    "EHRRecordType",
    "WearableDay",
    "LifestyleProfile",
    "VitalitySnapshot",
    # Slice 2
    "Protocol",
    "ProtocolAction",
    "DailyLog",
    "MealLog",
    "SurveyResponse",
    "VitalityOutlook",
    "Message",
    "Notification",
    "ClinicalReview",
    "Referral",
]
