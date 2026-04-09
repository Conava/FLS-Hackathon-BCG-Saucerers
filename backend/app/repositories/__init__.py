"""Repository layer for the Longevity+ backend.

All repositories inherit from ``PatientScopedRepository``, which enforces
``WHERE patient_id = :pid`` on every SQL query — the GDPR hard-isolation
invariant.

Import from here::

    from app.repositories import PatientScopedRepository
"""

from app.repositories.base import PatientScopedRepository

__all__ = ["PatientScopedRepository"]
