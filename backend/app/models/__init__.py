"""SQLModel table entities for the Longevity+ Unified Patient Profile.

Import from here for a clean API:
    from app.models import Patient, EHRRecord, WearableDay, LifestyleProfile, VitalitySnapshot

All models are imported here to ensure SQLModel metadata is populated before
create_all() is called (SQLModel discovers tables at import time).
"""

from app.models.ehr_record import EHRRecord, EHRRecordType
from app.models.lifestyle_profile import LifestyleProfile
from app.models.patient import Patient
from app.models.vitality_snapshot import VitalitySnapshot
from app.models.wearable_day import WearableDay

__all__ = [
    "Patient",
    "EHRRecord",
    "EHRRecordType",
    "WearableDay",
    "LifestyleProfile",
    "VitalitySnapshot",
]