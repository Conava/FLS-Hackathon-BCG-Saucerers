"""Repository layer for the Longevity+ backend.

All repositories enforce ``WHERE patient_id = :pid`` on every SQL query —
the GDPR hard-isolation invariant.  Child-table repositories inherit from
``PatientScopedRepository``; single-PK-is-patient_id repositories (Patient,
VitalitySnapshot) are thin dedicated classes that enforce the invariant
explicitly.

Import from here::

    from app.repositories import (
        PatientScopedRepository,
        PatientRepository,
        EHRRepository,
        WearableRepository,
        VitalityRepository,
    )
"""

from app.repositories.base import PatientScopedRepository
from app.repositories.ehr_repo import EHRRepository
from app.repositories.patient_repo import PatientRepository
from app.repositories.vitality_repo import VitalityRepository
from app.repositories.wearable_repo import WearableRepository

__all__ = [
    "PatientScopedRepository",
    "PatientRepository",
    "EHRRepository",
    "WearableRepository",
    "VitalityRepository",
]
