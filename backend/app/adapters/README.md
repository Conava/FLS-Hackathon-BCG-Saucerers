# Adapter Layer — Pluggable Data Sources

## Why this exists

Longevity+ ingests patient data from heterogeneous sources: today a flat CSV
export, tomorrow FHIR R4 endpoints, Apple Health bundles, Doctolib
appointments, or a proprietary EHR API. Without a stable abstraction,
every new source would require changes across services, repositories, and
tests.

The adapter layer provides a single seam: downstream services call
`get_source("csv")` (or `"fhir"`, or whatever) and iterate patients.
They never import a concrete adapter class. **Adding a new data source is
under 50 lines and zero changes to existing services.**

## Core abstractions

| Symbol | Module | Role |
|---|---|---|
| `PatientData` | `base.py` | Dataclass DTO — one bundle per patient |
| `DataSource` | `base.py` | `@runtime_checkable Protocol` — structural interface |
| `@register(name)` | `__init__.py` | Decorator — adds adapter class to registry |
| `get_source(name, **kwargs)` | `__init__.py` | Factory — resolves + instantiates |
| `list_sources()` | `__init__.py` | Introspection — lists all registered names |

`PatientData` is a plain `@dataclass` (not Pydantic) because it carries
SQLModel instances and needs no runtime validation overhead.

`DataSource` uses structural subtyping — no inheritance required. If a class
has `name: str` and `async def iter_patients(...)`, it satisfies the Protocol.

`iter_patients` is an **async generator** (not a list) so memory stays bounded
at one `PatientData` bundle at a time across 1 000+ patients.

## How to add a new adapter (skeleton)

Create `app/adapters/fhir_source.py`:

```python
from __future__ import annotations

from collections.abc import AsyncIterator

from app.adapters import register
from app.adapters.base import DataSource, PatientData
from app.models import EHRRecord, LifestyleProfile, Patient, WearableDay


@register("fhir")
class FHIRDataSource:
    """Streams patients from a FHIR R4 base URL."""

    name: str = "fhir"

    def __init__(self, base_url: str, api_key: str) -> None:
        self._base_url = base_url
        self._api_key = api_key

    async def iter_patients(self) -> AsyncIterator[PatientData]:
        # 1. Fetch patient bundle from FHIR server
        # 2. For each patient, fetch Observation / MedicationRequest resources
        # 3. Map to PatientData and yield — one at a time
        async for raw in self._fetch_pages("/Patient"):
            patient = Patient(patient_id=raw["id"], ...)
            yield PatientData(
                patient=patient,
                ehr_records=[...],
                wearable_days=[],   # FHIR doesn't expose wearable telemetry
                lifestyle=None,
            )
```

Then import it anywhere **before** calling `get_source("fhir")` so the
`@register` decorator fires:

```python
import app.adapters.fhir_source  # noqa: F401  — side-effect import
from app.adapters import get_source

source = get_source("fhir", base_url="https://hapi.fhir.org/baseR4", api_key="…")
async for pd in source.iter_patients():
    await session.merge(pd.patient)
```

That is the entire integration. No service code changes.

## Existing adapters

| Name | Module | Description |
|---|---|---|
| `csv` | `csv_source.py` | Loads the three bundled CSV datasets (T10) |
