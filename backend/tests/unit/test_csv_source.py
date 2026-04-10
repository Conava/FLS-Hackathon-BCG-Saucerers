"""Unit tests for CSVDataSource adapter — daily_log and meal_log extensions.

These tests cover the new daily_log.csv and meal_log.csv loading added in T2.
They use in-memory CSV fixtures written to tmp_path directories.

Test inventory
--------------
1. test_csv_source_daily_log_loaded        — adapter yields correct DailyLog rows
2. test_csv_source_meal_log_loaded         — adapter yields correct MealLog rows
3. test_csv_source_meal_log_macros_blob    — macros JSON is reconstructed correctly
4. test_csv_source_meal_log_manual_uri     — empty photo_uri gets deterministic manual:// sentinel
5. test_csv_source_missing_daily_log_file  — no daily_log.csv → empty list, no exception
6. test_csv_source_missing_meal_log_file   — no meal_log.csv → empty list, no exception
7. test_csv_source_daily_log_naive_datetimes — logged_at is tz-naive
8. test_csv_source_meal_log_naive_datetimes  — analyzed_at is tz-naive
"""

from __future__ import annotations

import datetime
import textwrap
import uuid
from pathlib import Path

import pytest

import app.adapters.csv_source  # noqa: F401 — side-effect: registers @register("csv")
from app.adapters import get_source
from app.adapters.base import PatientData
from app.models import DailyLog, MealLog

# ---------------------------------------------------------------------------
# Shared EHR/wearable/lifestyle boilerplate for a minimal one-patient fixture
# ---------------------------------------------------------------------------

_EHR_HEADER = (
    "patient_id,age,sex,country,height_cm,weight_kg,bmi,smoking_status,"
    "alcohol_units_weekly,chronic_conditions,icd_codes,n_chronic_conditions,"
    "medications,n_visits_2yr,visit_history,"
    "sbp_mmhg,dbp_mmhg,total_cholesterol_mmol,ldl_mmol,hdl_mmol,"
    "triglycerides_mmol,hba1c_pct,fasting_glucose_mmol,crp_mg_l,egfr_ml_min\n"
)

_EHR_ROW = (
    "PT0001,35,F,Germany,170.0,65.0,22.5,never,0,"
    "none,Z00.0,0,None,1,2023-01-01:Z00.0,"
    "120,80,5.0,3.0,1.5,1.0,5.0,4.5,0.5,90\n"
)

_WEARABLE_HEADER = (
    "patient_id,date,resting_hr_bpm,hrv_rmssd_ms,steps,active_minutes,"
    "sleep_duration_hrs,sleep_quality_score,deep_sleep_pct,spo2_avg_pct,"
    "calories_burned_kcal\n"
)

_WEARABLE_ROW = "PT0001,2026-01-01,62,45.0,8000,30,7.5,80.0,20.0,97.5,1700\n"

_LIFESTYLE_HEADER = (
    "patient_id,survey_date,smoking_status,alcohol_units_weekly,"
    "diet_quality_score,fruit_veg_servings_daily,meal_frequency_daily,"
    "exercise_sessions_weekly,sedentary_hrs_day,stress_level,sleep_satisfaction,"
    "mental_wellbeing_who5,self_rated_health,water_glasses_daily\n"
)

_LIFESTYLE_ROW = "PT0001,2026-01-01,never,0,7,3.0,3,4,6.0,3,7,70,7,8\n"

# ---------------------------------------------------------------------------
# daily_log CSV samples
# ---------------------------------------------------------------------------

_DAILY_LOG_HEADER = (
    "patient_id,logged_at,mood,workout_minutes,sleep_hours,water_ml,"
    "alcohol_units,sleep_quality,workout_type,workout_intensity\n"
)

_DAILY_LOG_ROWS = (
    "PT0001,2026-01-01T08:00:00,4,30,7.5,1800,0,4,walk,low\n"
    "PT0001,2026-01-02T08:00:00,3,0,6.8,1600,0,3,,\n"
    "PT0001,2026-01-03T08:00:00,5,45,7.8,2000,0,4,yoga,med\n"
)

# ---------------------------------------------------------------------------
# meal_log CSV samples
# ---------------------------------------------------------------------------

_MEAL_LOG_HEADER = (
    "patient_id,analyzed_at,photo_uri,protein_g,carbs_g,fat_g,fiber_g,"
    "calories_kcal,description,longevity_swap\n"
)

# Row 1: has explicit photo_uri
# Row 2: empty photo_uri → must generate manual:// sentinel
_MEAL_LOG_ROWS = (
    "PT0001,2026-01-01T12:00:00,manual://test-uri,32,38,14,9,420,"
    "Grilled salmon bowl,Swap white rice for quinoa\n"
    "PT0001,2026-01-02T13:00:00,,28,45,10,6,380,"
    "Chicken pasta,Add more vegetables\n"
)


# ---------------------------------------------------------------------------
# Fixture helper
# ---------------------------------------------------------------------------


def _write_base_files(tmp: Path) -> None:
    """Write EHR, wearable, and lifestyle CSVs for PT0001 into tmp dir."""
    (tmp / "ehr_records.csv").write_text(_EHR_HEADER + _EHR_ROW)
    (tmp / "wearable_telemetry_1.csv").write_text(_WEARABLE_HEADER + _WEARABLE_ROW)
    (tmp / "lifestyle_survey.csv").write_text(_LIFESTYLE_HEADER + _LIFESTYLE_ROW)


def _write_daily_log(tmp: Path) -> None:
    """Write daily_log.csv for PT0001 into tmp dir (3 rows)."""
    (tmp / "daily_log.csv").write_text(_DAILY_LOG_HEADER + _DAILY_LOG_ROWS)


def _write_meal_log(tmp: Path) -> None:
    """Write meal_log.csv for PT0001 into tmp dir (2 rows)."""
    (tmp / "meal_log.csv").write_text(_MEAL_LOG_HEADER + _MEAL_LOG_ROWS)


async def _collect(data_dir: Path) -> list[PatientData]:
    """Drain CSVDataSource into a list."""
    source = get_source("csv", data_dir=data_dir)
    results: list[PatientData] = []
    async for pd in source.iter_patients():  # type: ignore[attr-defined]
        results.append(pd)
    return results


# ---------------------------------------------------------------------------
# Tests — daily_log
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_csv_source_daily_log_loaded(tmp_path: Path) -> None:
    """Adapter yields 3 DailyLog rows for PT0001 when daily_log.csv is present."""
    _write_base_files(tmp_path)
    _write_daily_log(tmp_path)

    patients = await _collect(tmp_path)
    assert len(patients) == 1
    pt = patients[0]
    assert pt.patient.patient_id == "PT0001"

    logs = pt.daily_logs
    assert len(logs) == 3

    # Verify first row fields
    first = next(l for l in logs if l.logged_at == datetime.datetime(2026, 1, 1, 8, 0, 0))
    assert first.patient_id == "PT0001"
    assert first.mood == 4
    assert first.workout_minutes == 30
    assert first.sleep_hours == pytest.approx(7.5)
    assert first.water_ml == 1800
    assert first.alcohol_units == pytest.approx(0.0)
    assert first.sleep_quality == 4
    assert first.workout_type == "walk"
    assert first.workout_intensity == "low"


@pytest.mark.asyncio
async def test_csv_source_daily_log_optional_fields(tmp_path: Path) -> None:
    """Row 2 has empty workout_type/intensity — must produce None, not empty string."""
    _write_base_files(tmp_path)
    _write_daily_log(tmp_path)

    patients = await _collect(tmp_path)
    pt = patients[0]

    second = next(l for l in pt.daily_logs if l.logged_at == datetime.datetime(2026, 1, 2, 8, 0, 0))
    assert second.workout_type is None
    assert second.workout_intensity is None


@pytest.mark.asyncio
async def test_csv_source_daily_log_naive_datetimes(tmp_path: Path) -> None:
    """All DailyLog.logged_at values must be tz-naive (asyncpg requirement)."""
    _write_base_files(tmp_path)
    _write_daily_log(tmp_path)

    patients = await _collect(tmp_path)
    for log in patients[0].daily_logs:
        assert log.logged_at.tzinfo is None, (
            f"DailyLog.logged_at has tzinfo: {log.logged_at.tzinfo}"
        )


# ---------------------------------------------------------------------------
# Tests — meal_log
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_csv_source_meal_log_loaded(tmp_path: Path) -> None:
    """Adapter yields 2 MealLog rows for PT0001 when meal_log.csv is present."""
    _write_base_files(tmp_path)
    _write_meal_log(tmp_path)

    patients = await _collect(tmp_path)
    pt = patients[0]

    meals = pt.meal_logs
    assert len(meals) == 2


@pytest.mark.asyncio
async def test_csv_source_meal_log_macros_blob(tmp_path: Path) -> None:
    """meal_log macros JSON blob is reconstructed correctly from flat columns."""
    _write_base_files(tmp_path)
    _write_meal_log(tmp_path)

    patients = await _collect(tmp_path)
    pt = patients[0]

    first = next(m for m in pt.meal_logs if m.analyzed_at == datetime.datetime(2026, 1, 1, 12, 0, 0))
    assert first.macros is not None
    assert first.macros["protein_g"] == pytest.approx(32.0)
    assert first.macros["carbs_g"] == pytest.approx(38.0)
    assert first.macros["fat_g"] == pytest.approx(14.0)
    assert first.macros["fiber_g"] == pytest.approx(9.0)
    assert first.macros["calories_kcal"] == pytest.approx(420.0)
    assert first.macros["description"] == "Grilled salmon bowl"
    assert first.longevity_swap == "Swap white rice for quinoa"


@pytest.mark.asyncio
async def test_csv_source_meal_log_explicit_photo_uri(tmp_path: Path) -> None:
    """Row with explicit photo_uri preserves it as-is."""
    _write_base_files(tmp_path)
    _write_meal_log(tmp_path)

    patients = await _collect(tmp_path)
    pt = patients[0]

    first = next(m for m in pt.meal_logs if m.analyzed_at == datetime.datetime(2026, 1, 1, 12, 0, 0))
    assert first.photo_uri == "manual://test-uri"


@pytest.mark.asyncio
async def test_csv_source_meal_log_manual_uri_generated(tmp_path: Path) -> None:
    """Row with empty photo_uri gets a deterministic manual:// sentinel URI.

    The sentinel uses uuid.uuid5(NAMESPACE_DNS, 'patient_id:analyzed_at_str')
    so the same input always produces the same URI (idempotent re-ingest).
    """
    _write_base_files(tmp_path)
    _write_meal_log(tmp_path)

    patients = await _collect(tmp_path)
    pt = patients[0]

    second = next(m for m in pt.meal_logs if m.analyzed_at == datetime.datetime(2026, 1, 2, 13, 0, 0))
    assert second.photo_uri.startswith("manual://")

    # Verify determinism: the same input must produce the same UUID
    expected_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, "PT0001:2026-01-02T13:00:00")
    assert second.photo_uri == f"manual://{expected_uuid}"


@pytest.mark.asyncio
async def test_csv_source_meal_log_naive_datetimes(tmp_path: Path) -> None:
    """All MealLog.analyzed_at values must be tz-naive (asyncpg requirement)."""
    _write_base_files(tmp_path)
    _write_meal_log(tmp_path)

    patients = await _collect(tmp_path)
    for meal in patients[0].meal_logs:
        assert meal.analyzed_at.tzinfo is None, (
            f"MealLog.analyzed_at has tzinfo: {meal.analyzed_at.tzinfo}"
        )


# ---------------------------------------------------------------------------
# Tests — missing-file tolerance
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_csv_source_missing_daily_log_file(tmp_path: Path) -> None:
    """Missing daily_log.csv must yield patients with empty daily_logs — no exception."""
    _write_base_files(tmp_path)
    # Intentionally do NOT write daily_log.csv

    patients = await _collect(tmp_path)
    assert len(patients) == 1
    assert patients[0].daily_logs == []


@pytest.mark.asyncio
async def test_csv_source_missing_meal_log_file(tmp_path: Path) -> None:
    """Missing meal_log.csv must yield patients with empty meal_logs — no exception."""
    _write_base_files(tmp_path)
    # Intentionally do NOT write meal_log.csv

    patients = await _collect(tmp_path)
    assert len(patients) == 1
    assert patients[0].meal_logs == []


@pytest.mark.asyncio
async def test_csv_source_both_missing_files(tmp_path: Path) -> None:
    """Missing both daily_log.csv and meal_log.csv must be fully transparent."""
    _write_base_files(tmp_path)

    patients = await _collect(tmp_path)
    assert len(patients) == 1
    pt = patients[0]
    assert pt.daily_logs == []
    assert pt.meal_logs == []
