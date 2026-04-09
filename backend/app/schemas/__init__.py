"""Pydantic v2 response schemas (DTOs) for the Longevity+ API.

All schemas are BaseModel subclasses with ``ConfigDict(from_attributes=True)``
so they can be constructed from ORM model instances (SQLModel / SQLAlchemy).

Wellness framing invariant: no field name in any schema may contain the words
``diagnose``, ``diagnosis``, ``treat``, ``cure``, or ``prevent_disease``.
This is enforced by the ``test_no_diagnostic_verbs_in_field_names`` test.
"""

from app.schemas.appointments import AppointmentListOut, AppointmentOut
from app.schemas.gdpr import GDPRDeleteAck, GDPRExportOut
from app.schemas.insights import InsightOut, InsightsListOut
from app.schemas.patient import PatientProfileOut
from app.schemas.records import EHRRecordListOut, EHRRecordOut
from app.schemas.vitality import TrendPoint, VitalityOut
from app.schemas.wearable import WearableDayOut, WearableSeriesOut

__all__ = [
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
]
