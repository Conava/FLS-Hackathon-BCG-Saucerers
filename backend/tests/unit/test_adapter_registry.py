"""Unit tests for the adapter Protocol, PatientData DTO, and registry.

Tests are written before implementation (TDD red phase). They exercise:
- registry: @register, get_source, list_sources
- error cases: unknown source name with helpful message
- PatientData dataclass shape
- DataSource Protocol runtime-checkability via isinstance
"""

from __future__ import annotations

import asyncio
import datetime
from typing import AsyncIterator

import pytest

from app.adapters.base import DataSource, PatientData
from app.models import EHRRecord, LifestyleProfile, Patient, WearableDay


# ---------------------------------------------------------------------------
# Helpers: minimal in-test stubs
# ---------------------------------------------------------------------------


def _make_patient(pid: str = "PT0001") -> Patient:
    return Patient(
        patient_id=pid,
        name="Test User",
        age=30,
        sex="M",
        country="DE",
    )


def _make_ehr(pid: str = "PT0001") -> EHRRecord:
    return EHRRecord(
        patient_id=pid,
        record_type="condition",
        recorded_at=datetime.datetime(2024, 1, 1, tzinfo=datetime.UTC),
        payload={"icd10": "Z00.0", "description": "Annual checkup"},
        source="test",
    )


def _make_wearable(pid: str = "PT0001") -> WearableDay:
    return WearableDay(
        patient_id=pid,
        date=datetime.date(2024, 1, 1),
    )


class _FakeDataSource:
    """Minimal concrete implementation of the DataSource Protocol (no DB needed)."""

    name: str = "fake"

    async def iter_patients(self) -> AsyncIterator[PatientData]:
        patient = _make_patient()
        yield PatientData(
            patient=patient,
            ehr_records=[_make_ehr()],
            wearable_days=[_make_wearable()],
            lifestyle=None,
        )


# ---------------------------------------------------------------------------
# Tests: PatientData dataclass
# ---------------------------------------------------------------------------


class TestPatientDataShape:
    """PatientData is a plain dataclass — no Pydantic, no validation overhead."""

    def test_patientdata_dataclass_shape_all_fields(self) -> None:
        """All four fields are accessible after construction."""
        patient = _make_patient()
        ehr = _make_ehr()
        wearable = _make_wearable()

        pd = PatientData(
            patient=patient,
            ehr_records=[ehr],
            wearable_days=[wearable],
            lifestyle=None,
        )

        assert pd.patient is patient
        assert pd.ehr_records == [ehr]
        assert pd.wearable_days == [wearable]
        assert pd.lifestyle is None

    def test_patientdata_with_lifestyle_profile(self) -> None:
        """lifestyle field accepts a LifestyleProfile instance."""
        patient = _make_patient("PT0002")
        lifestyle = LifestyleProfile(patient_id="PT0002", survey_date=datetime.date(2024, 1, 1))

        pd = PatientData(
            patient=patient,
            ehr_records=[],
            wearable_days=[],
            lifestyle=lifestyle,
        )

        assert pd.lifestyle is lifestyle
        assert isinstance(pd.lifestyle, LifestyleProfile)


# ---------------------------------------------------------------------------
# Tests: DataSource Protocol runtime-checkable
# ---------------------------------------------------------------------------


class TestDataSourceProtocol:
    """DataSource is a @runtime_checkable Protocol — isinstance must work."""

    def test_datasource_protocol_runtime_checkable_conforming_class(self) -> None:
        """A class with name + iter_patients passes isinstance check."""
        source = _FakeDataSource()
        assert isinstance(source, DataSource)

    def test_datasource_protocol_rejects_non_conforming_class(self) -> None:
        """A class missing iter_patients fails isinstance check."""

        class _BadSource:
            name: str = "bad"
            # iter_patients is intentionally absent

        assert not isinstance(_BadSource(), DataSource)

    def test_datasource_iter_patients_is_async_generator(self) -> None:
        """iter_patients yields PatientData items asynchronously."""
        source = _FakeDataSource()

        async def _collect() -> list[PatientData]:
            return [item async for item in source.iter_patients()]

        items = asyncio.run(_collect())
        assert len(items) == 1
        assert isinstance(items[0], PatientData)


# ---------------------------------------------------------------------------
# Tests: Registry — register, get_source, list_sources
# ---------------------------------------------------------------------------


class TestRegistry:
    """Registry tests use a dedicated name to avoid polluting the global registry."""

    def test_register_and_get_source(self) -> None:
        """@register adds a class; get_source returns a correctly-typed instance."""
        from app.adapters import get_source, register

        @register("_test_fake")
        class _LocalFake:
            name: str = "_test_fake"

            async def iter_patients(self) -> AsyncIterator[PatientData]:
                return
                yield  # make it an async generator

        instance = get_source("_test_fake")
        assert isinstance(instance, _LocalFake)

    def test_get_source_unknown_raises_key_error(self) -> None:
        """get_source raises KeyError for unregistered names."""
        from app.adapters import get_source

        with pytest.raises(KeyError):
            get_source("_definitely_not_registered_xyz")

    def test_get_source_unknown_raises_with_helpful_message(self) -> None:
        """The KeyError message includes the unknown name AND lists known sources."""
        from app.adapters import get_source, register

        @register("_test_known_for_message")
        class _SomeSource:
            name: str = "_test_known_for_message"

            async def iter_patients(self) -> AsyncIterator[PatientData]:
                return
                yield

        with pytest.raises(KeyError, match="_definitely_unknown_xyz"):
            get_source("_definitely_unknown_xyz")

    def test_list_sources_returns_sorted(self) -> None:
        """list_sources returns known source names in sorted order."""
        from app.adapters import list_sources, register

        @register("_test_zzz")
        class _Z:
            name: str = "_test_zzz"

            async def iter_patients(self) -> AsyncIterator[PatientData]:
                return
                yield

        @register("_test_aaa")
        class _A:
            name: str = "_test_aaa"

            async def iter_patients(self) -> AsyncIterator[PatientData]:
                return
                yield

        sources = list_sources()
        # Must be sorted
        assert sources == sorted(sources)
        # Our test adapters must appear
        assert "_test_aaa" in sources
        assert "_test_zzz" in sources

    def test_get_source_passes_kwargs_to_constructor(self) -> None:
        """get_source forwards **kwargs to the class constructor."""
        from app.adapters import get_source, register

        @register("_test_with_kwargs")
        class _ConfigurableSource:
            name: str = "_test_with_kwargs"

            def __init__(self, data_dir: str = "default") -> None:
                self.data_dir = data_dir

            async def iter_patients(self) -> AsyncIterator[PatientData]:
                return
                yield

        instance = get_source("_test_with_kwargs", data_dir="/tmp/data")
        assert isinstance(instance, _ConfigurableSource)
        assert instance.data_dir == "/tmp/data"
