"""Repository layer for the Longevity+ backend.

All repositories enforce ``WHERE patient_id = :pid`` on every SQL query —
the GDPR hard-isolation invariant.  Child-table repositories inherit from
``PatientScopedRepository``; single-PK-is-patient_id repositories (Patient,
VitalitySnapshot) are thin dedicated classes that enforce the invariant
explicitly.

ProtocolAction has no ``patient_id`` column — its isolation is enforced
via a two-step subquery through the parent Protocol table.  See
``ProtocolActionRepository`` for details.

Import from here::

    from app.repositories import (
        PatientScopedRepository,
        PatientRepository,
        EHRRepository,
        WearableRepository,
        VitalityRepository,
        ProtocolRepository,
        ProtocolActionRepository,
        DailyLogRepository,
        MealLogRepository,
        SurveyRepository,
        VitalityOutlookRepository,
        MessageRepository,
        NotificationRepository,
        ClinicalReviewRepository,
        ReferralRepository,
    )
"""

from app.repositories.base import PatientScopedRepository
from app.repositories.clinical_review_repo import ClinicalReviewRepository
from app.repositories.daily_log_repo import DailyLogRepository
from app.repositories.ehr_repo import EHRRepository
from app.repositories.meal_log_repo import MealLogRepository
from app.repositories.message_repo import MessageRepository
from app.repositories.notification_repo import NotificationRepository
from app.repositories.outlook_repo import VitalityOutlookRepository
from app.repositories.patient_repo import PatientRepository
from app.repositories.protocol_repo import ProtocolActionRepository, ProtocolRepository
from app.repositories.referral_repo import ReferralRepository
from app.repositories.survey_repo import SurveyRepository
from app.repositories.vitality_repo import VitalityRepository
from app.repositories.wearable_repo import WearableRepository

__all__ = [
    # Base
    "PatientScopedRepository",
    # Slice 1
    "PatientRepository",
    "EHRRepository",
    "WearableRepository",
    "VitalityRepository",
    # Slice 2
    "ProtocolRepository",
    "ProtocolActionRepository",
    "DailyLogRepository",
    "MealLogRepository",
    "SurveyRepository",
    "VitalityOutlookRepository",
    "MessageRepository",
    "NotificationRepository",
    "ClinicalReviewRepository",
    "ReferralRepository",
]
