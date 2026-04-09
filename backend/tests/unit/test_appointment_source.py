"""Unit tests for AppointmentSource Protocol and StaticAppointmentSource.

Tests follow strict TDD order:
1. Protocol conformance (isinstance check)
2. PT0282 fixture: two appointments, correct order
3. PT0282 fixture: exact field values for Cardio-Prevention Panel
4. Generic patient fixture: one annual check-up
5. All datetimes are naive (UTC, no tzinfo)
6. get_appointment_source returns the module-level singleton
"""

from __future__ import annotations

import asyncio
import datetime

import pytest

from app.adapters.appointment_source import (
    Appointment,
    AppointmentSource,
    StaticAppointmentSource,
    get_appointment_source,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run(coro: object) -> object:
    """Run a coroutine synchronously (tests are not async)."""
    import asyncio as _asyncio

    return _asyncio.run(coro)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Protocol conformance
# ---------------------------------------------------------------------------


class TestProtocolConformance:
    """StaticAppointmentSource must satisfy AppointmentSource at runtime."""

    def test_static_source_conforms_to_protocol(self) -> None:
        """isinstance(StaticAppointmentSource(), AppointmentSource) is True."""
        source = StaticAppointmentSource()
        assert isinstance(source, AppointmentSource)

    def test_static_source_has_name_attribute(self) -> None:
        """Protocol requires a ``name`` class attribute."""
        assert StaticAppointmentSource.name == "static"

    def test_plain_object_does_not_conform(self) -> None:
        """A random object does not satisfy the Protocol."""

        class _NoListFor:
            name: str = "fake"

        assert not isinstance(_NoListFor(), AppointmentSource)


# ---------------------------------------------------------------------------
# PT0282 — Anna Weber fixture
# ---------------------------------------------------------------------------


class TestStaticSourcePT0282:
    """The static stub returns the Cardio + Sleep appointments for PT0282."""

    def _list(self, patient_id: str = "PT0282") -> list[Appointment]:
        source = StaticAppointmentSource()
        return asyncio.run(source.list_for(patient_id))

    def test_static_source_pt0282_has_two_appointments(self) -> None:
        """PT0282 receives exactly two upcoming appointments."""
        appts = self._list("PT0282")
        assert len(appts) == 2

    def test_static_source_pt0282_appointments_in_expected_order(self) -> None:
        """Cardio panel (Apr 14) comes before Sleep assessment (Apr 17)."""
        appts = self._list("PT0282")
        assert appts[0].starts_at < appts[1].starts_at

    def test_static_source_pt0282_cardio_panel_title(self) -> None:
        """First appointment title matches the mockup copy exactly."""
        appts = self._list("PT0282")
        assert appts[0].title == "Cardio-Prevention Panel"

    def test_static_source_pt0282_cardio_panel_exact_fields(self) -> None:
        """Every field of the Cardio-Prevention Panel must match the spec."""
        appts = self._list("PT0282")
        cardio = appts[0]

        assert cardio.id == "appt-pt0282-cardio"
        assert cardio.title == "Cardio-Prevention Panel"
        assert cardio.provider == "Dr. Mehlhorn"
        assert cardio.location == "Hamburg-Eppendorf"
        assert cardio.starts_at == datetime.datetime(2026, 4, 14, 14, 30)
        assert cardio.duration_minutes == 45
        assert cardio.price_eur == 79.0
        assert cardio.covered_percent == 80

    def test_static_source_pt0282_sleep_assessment_exact_fields(self) -> None:
        """Every field of the Sleep Assessment must match the spec."""
        appts = self._list("PT0282")
        sleep = appts[1]

        assert sleep.id == "appt-pt0282-sleep"
        assert sleep.title == "Sleep Assessment"
        assert sleep.provider == "Dr. Klein"
        assert sleep.location == "Tele-consult"
        assert sleep.starts_at == datetime.datetime(2026, 4, 17, 9, 0)
        assert sleep.duration_minutes == 30
        assert sleep.price_eur == 45.0
        assert sleep.covered_percent == 80


# ---------------------------------------------------------------------------
# Generic patient fixture
# ---------------------------------------------------------------------------


class TestStaticSourceGenericPatient:
    """All non-PT0282 patient IDs get a single generic annual check-up."""

    def _list(self, patient_id: str) -> list[Appointment]:
        source = StaticAppointmentSource()
        return asyncio.run(source.list_for(patient_id))

    def test_static_source_other_patient_has_generic_checkup(self) -> None:
        """Any patient other than PT0282 gets exactly one appointment."""
        appts = self._list("PT0001")
        assert len(appts) == 1

    def test_static_source_generic_checkup_title(self) -> None:
        """Generic appointment title must match spec."""
        appts = self._list("PT9999")
        assert appts[0].title == "Annual Check-up"

    def test_static_source_generic_checkup_no_price_or_coverage(self) -> None:
        """Generic appointment has no billing information."""
        appts = self._list("PT0100")
        appt = appts[0]
        assert appt.price_eur is None
        assert appt.covered_percent is None

    def test_static_source_generic_checkup_deterministic_date(self) -> None:
        """Same patient ID always returns the same date."""
        appts1 = self._list("PT0050")
        appts2 = self._list("PT0050")
        assert appts1[0].starts_at == appts2[0].starts_at

    def test_static_source_generic_checkup_date_is_2026_06_22(self) -> None:
        """Generic appointment is on 2026-06-22 10:00 per spec."""
        appts = self._list("PT0001")
        assert appts[0].starts_at == datetime.datetime(2026, 6, 22, 10, 0)


# ---------------------------------------------------------------------------
# Datetime naivety
# ---------------------------------------------------------------------------


class TestAppointmentDatetimes:
    """All starts_at values must be naive UTC (no tzinfo)."""

    def test_appointments_have_naive_datetimes(self) -> None:
        """Both PT0282 and generic patients have naive starts_at datetimes."""
        source = StaticAppointmentSource()
        pt0282_appts = asyncio.run(source.list_for("PT0282"))
        generic_appts = asyncio.run(source.list_for("PT0001"))

        for appt in pt0282_appts + generic_appts:
            assert appt.starts_at.tzinfo is None, (
                f"Expected naive datetime, got tzinfo={appt.starts_at.tzinfo!r} "
                f"on appointment {appt.id!r}"
            )


# ---------------------------------------------------------------------------
# Appointment dataclass
# ---------------------------------------------------------------------------


class TestAppointmentDataclass:
    """Appointment is a plain dataclass with the specified fields."""

    def test_appointment_can_be_constructed_directly(self) -> None:
        """Appointment dataclass accepts all fields positionally or by keyword."""
        appt = Appointment(
            id="test-1",
            title="Test Appointment",
            provider="Dr. Test",
            location="Test Clinic",
            starts_at=datetime.datetime(2026, 5, 1, 9, 0),
            duration_minutes=30,
            price_eur=50.0,
            covered_percent=75,
        )
        assert appt.id == "test-1"
        assert appt.price_eur == 50.0
        assert appt.covered_percent == 75

    def test_appointment_optional_fields_accept_none(self) -> None:
        """price_eur and covered_percent can be None."""
        appt = Appointment(
            id="test-2",
            title="Free Check",
            provider="Dr. Free",
            location="Community Clinic",
            starts_at=datetime.datetime(2026, 5, 2, 10, 0),
            duration_minutes=20,
            price_eur=None,
            covered_percent=None,
        )
        assert appt.price_eur is None
        assert appt.covered_percent is None


# ---------------------------------------------------------------------------
# Singleton helper
# ---------------------------------------------------------------------------


class TestGetAppointmentSource:
    """get_appointment_source returns the module-level default singleton."""

    def test_get_appointment_source_returns_default_singleton(self) -> None:
        """get_appointment_source() returns a StaticAppointmentSource instance."""
        source = get_appointment_source()
        assert isinstance(source, StaticAppointmentSource)

    def test_get_appointment_source_is_appointment_source_protocol(self) -> None:
        """The returned instance satisfies the AppointmentSource Protocol."""
        source = get_appointment_source()
        assert isinstance(source, AppointmentSource)

    def test_get_appointment_source_returns_same_object(self) -> None:
        """Calling twice returns the same object (module-level singleton)."""
        source1 = get_appointment_source()
        source2 = get_appointment_source()
        assert source1 is source2


# ---------------------------------------------------------------------------
# Wellness framing guard
# ---------------------------------------------------------------------------


class TestWellnessFraming:
    """Appointment titles and provider names must not contain diagnostic verbs."""

    _DIAGNOSTIC_VERBS = {"diagnose", "treat", "cure", "prevent-disease", "prescribe"}

    def _all_appointments(self) -> list[Appointment]:
        source = StaticAppointmentSource()
        pt0282 = asyncio.run(source.list_for("PT0282"))
        generic = asyncio.run(source.list_for("PT0001"))
        return pt0282 + generic

    def test_no_diagnostic_verbs_in_titles(self) -> None:
        """Appointment titles must use wellness framing."""
        for appt in self._all_appointments():
            for verb in self._DIAGNOSTIC_VERBS:
                assert verb.lower() not in appt.title.lower(), (
                    f"Diagnostic verb {verb!r} found in title {appt.title!r}"
                )

    def test_no_diagnostic_verbs_in_providers(self) -> None:
        """Provider names must not contain diagnostic verbs."""
        for appt in self._all_appointments():
            for verb in self._DIAGNOSTIC_VERBS:
                assert verb.lower() not in appt.provider.lower(), (
                    f"Diagnostic verb {verb!r} found in provider {appt.provider!r}"
                )
