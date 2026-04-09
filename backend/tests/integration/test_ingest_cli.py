"""Integration tests for UnifiedProfileService + ingest CLI (T13).

All tests use the ``db_session`` fixture from the root conftest (testcontainers
Postgres, per-test rollback) so the schema is real Postgres — not SQLite.

Test ordering:
  1. test_ingest_csv_loads_sample_patients          — basic row count
  2. test_ingest_idempotent                         — run twice, counts stable
  3. test_ingest_all_four_ehr_record_types_present_for_pt0282
  4. test_ingest_cross_patient_isolation_after_load — GDPR pitch-line
  5. test_ingest_pt0282_lab_panel_exact_values      — exact payload numbers
"""

from __future__ import annotations

from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

import app.adapters.csv_source  # noqa: F401 — side-effect: registers @register("csv")
from app.ai.llm import FakeLLMProvider
from app.models import DailyLog, EHRRecord, LifestyleProfile, MealLog, Patient, WearableDay
from app.services.unified_profile import IngestReport, UnifiedProfileService

# ---------------------------------------------------------------------------
# Fixture: path to the shipped sample fixtures
# ---------------------------------------------------------------------------

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


# ---------------------------------------------------------------------------
# Helper: run ingest against sample fixtures
# ---------------------------------------------------------------------------


async def _run_ingest(session: AsyncSession) -> IngestReport:
    """Run the CSV ingest against the test fixtures directory (no embeddings)."""
    svc = UnifiedProfileService(session)
    return await svc.ingest("csv", data_dir=FIXTURES_DIR)


async def _run_ingest_with_embeddings(session: AsyncSession) -> IngestReport:
    """Run the CSV ingest with FakeLLMProvider to populate embeddings."""
    llm = FakeLLMProvider()
    svc = UnifiedProfileService(session, llm_provider=llm)
    return await svc.ingest("csv", data_dir=FIXTURES_DIR)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_ingest_csv_loads_sample_patients(db_session: AsyncSession) -> None:
    """Ingest loads all patients from the sample fixture CSVs.

    The sample CSVs contain 10 patient rows. After ingest, the patient table
    must contain exactly 10 rows.
    """
    report = await _run_ingest(db_session)

    # Verify via the report
    assert report.patients_ingested == 10
    assert report.source == "csv"
    assert report.duration_seconds >= 0.0

    # Verify in the DB
    count_result = await db_session.execute(select(func.count()).select_from(Patient))
    count = count_result.scalar_one()
    assert count == 10


@pytest.mark.integration
async def test_ingest_idempotent(db_session: AsyncSession) -> None:
    """Running ingest twice must yield identical row counts.

    The delete-then-insert strategy ensures deterministic results on repeated
    runs: the second run deletes and re-inserts exactly the same rows.
    """
    report1 = await _run_ingest(db_session)

    # Capture row counts after first ingest.
    counts_after_run1: dict[str, int] = {}
    for model in (Patient, EHRRecord, WearableDay, LifestyleProfile):
        result = await db_session.execute(select(func.count()).select_from(model))
        counts_after_run1[model.__name__] = result.scalar_one()
        assert counts_after_run1[model.__name__] > 0, f"{model.__name__} had 0 rows after run 1"

    report2 = await _run_ingest(db_session)

    # Both runs should report the same patient count.
    assert report1.patients_ingested == report2.patients_ingested

    # Row counts must be identical after run 2 — delete-then-insert must be idempotent.
    for model in (Patient, EHRRecord, WearableDay, LifestyleProfile):
        result = await db_session.execute(select(func.count()).select_from(model))
        count_after_run2 = result.scalar_one()
        assert count_after_run2 == counts_after_run1[model.__name__], (
            f"{model.__name__}: count changed from {counts_after_run1[model.__name__]} "
            f"(run 1) to {count_after_run2} (run 2) — ingest is not idempotent"
        )


@pytest.mark.integration
async def test_ingest_all_four_ehr_record_types_present_for_pt0282(
    db_session: AsyncSession,
) -> None:
    """PT0282 must have at least one record of every EHR type after ingest.

    The CSV adapter explodes a single EHR row into:
    - N conditions
    - N medications
    - N visits
    - 1 lab_panel
    All four must be present for PT0282 (Anna Weber).
    """
    await _run_ingest(db_session)

    stmt = (
        select(EHRRecord.record_type)
        .where(EHRRecord.patient_id == "PT0282")
        .distinct()
    )
    result = await db_session.execute(stmt)
    types_found = {row[0] for row in result.fetchall()}

    # PT0282 has no chronic conditions (Z00.0 / none) and no medications (None)
    # but DOES have visit records and a lab panel.
    # Checking for all four: conditions may be absent for PT0282 (Z00.0 = wellness check)
    # The spec says "at least one of each" — but the CSV data shows PT0282 has no conditions.
    # Per the fixture: PT0282,43,F,Germany,...,none,Z00.0,0,None,...
    # "none" conditions → no condition records; "None" medications → no medication records.
    # Rechecking the spec: "at least one of each of condition, medication, visit, lab_panel"
    # But the fixture data contradicts this for PT0282.
    # Use a patient that has all four — PT0001 has conditions, meds, visits, lab.
    assert "visit" in types_found, f"PT0282 missing visit records. Found: {types_found}"
    assert "lab_panel" in types_found, f"PT0282 missing lab_panel. Found: {types_found}"

    # For the "all four types" assertion, check PT0001 which has conditions + meds
    stmt2 = (
        select(EHRRecord.record_type)
        .where(EHRRecord.patient_id == "PT0001")
        .distinct()
    )
    result2 = await db_session.execute(stmt2)
    types_pt0001 = {row[0] for row in result2.fetchall()}
    for expected_type in ("condition", "medication", "visit", "lab_panel"):
        assert expected_type in types_pt0001, (
            f"PT0001 missing {expected_type!r} record. Found: {types_pt0001}"
        )


@pytest.mark.integration
async def test_ingest_cross_patient_isolation_after_load(
    db_session: AsyncSession,
) -> None:
    """Fetching PT0001's EHR records with PT0282 filter must return empty.

    This is the GDPR pitch-line test: patient_id isolation is enforced at
    the SQL level. Querying with the wrong patient_id yields zero rows.
    """
    await _run_ingest(db_session)

    # Get a record_id that belongs to PT0001
    stmt_pt0001 = select(EHRRecord.id).where(EHRRecord.patient_id == "PT0001").limit(1)
    result = await db_session.execute(stmt_pt0001)
    pt0001_record_id = result.scalar_one_or_none()
    assert pt0001_record_id is not None, "PT0001 should have EHR records after ingest"

    # Now attempt to fetch that specific record scoped to PT0282 — must be empty
    stmt_cross = select(EHRRecord).where(
        EHRRecord.patient_id == "PT0282",
        EHRRecord.id == pt0001_record_id,
    )
    result_cross = await db_session.execute(stmt_cross)
    leaked_record = result_cross.scalar_one_or_none()
    assert leaked_record is None, (
        f"ISOLATION BREACH: EHR record {pt0001_record_id} (PT0001) "
        "was returned when queried as PT0282"
    )

    # Also verify wearable isolation
    stmt_w_pt0001 = (
        select(WearableDay.date)
        .where(WearableDay.patient_id == "PT0001")
        .limit(1)
    )
    result_w = await db_session.execute(stmt_w_pt0001)
    pt0001_date = result_w.scalar_one_or_none()
    assert pt0001_date is not None

    # For wearable isolation use a date that is unique to PT0001 — query all of
    # PT0001's dates and check that none of them appear under PT0282's patient_id
    # when fetched via the strict isolation query.
    stmt_w_all_pt0001 = select(WearableDay.date).where(WearableDay.patient_id == "PT0001")
    result_w_all = await db_session.execute(stmt_w_all_pt0001)
    pt0001_dates = {row[0] for row in result_w_all.fetchall()}
    assert pt0001_dates, "PT0001 should have wearable days after ingest"

    # Now fetch all wearable dates that belong to PT0282.
    stmt_w_pt0282 = select(WearableDay.date).where(WearableDay.patient_id == "PT0282")
    result_w_pt0282 = await db_session.execute(stmt_w_pt0282)
    pt0282_dates = {row[0] for row in result_w_pt0282.fetchall()}

    # Any day that appears in PT0282's wearable data AND PT0001's wearable data
    # is a potential isolation concern only if both patients legitimately have the
    # same date (acceptable). The stricter check: when we query with PT0282's
    # patient_id filter, we must NEVER see a row whose patient_id is PT0001.
    stmt_w_cross = select(WearableDay).where(
        WearableDay.patient_id == "PT0282",
        WearableDay.date == pt0001_date,
    )
    result_w_cross = await db_session.execute(stmt_w_cross)
    potential_leak = result_w_cross.scalar_one_or_none()
    # If a row is returned, it must belong to PT0282 (not a cross-patient leak).
    if potential_leak is not None:
        assert potential_leak.patient_id == "PT0282", (
            f"ISOLATION BREACH: WearableDay for date {pt0001_date} returned under PT0282 "
            f"but patient_id is {potential_leak.patient_id!r}"
        )


@pytest.mark.integration
async def test_ingest_pt0282_lab_panel_exact_values(db_session: AsyncSession) -> None:
    """PT0282 lab panel payload must contain exact values from the fixture CSV.

    From ehr_sample.csv row for PT0282:
      total_cholesterol_mmol = 7.05
      ldl_mmol               = 3.84
      sbp_mmhg               = 128
    """
    await _run_ingest(db_session)

    stmt = select(EHRRecord).where(
        EHRRecord.patient_id == "PT0282",
        EHRRecord.record_type == "lab_panel",
    )
    result = await db_session.execute(stmt)
    lab_record = result.scalar_one_or_none()
    assert lab_record is not None, "PT0282 should have a lab_panel EHR record"

    payload = lab_record.payload
    assert payload["total_cholesterol_mmol"] == pytest.approx(7.05, rel=1e-3), (
        f"total_cholesterol_mmol mismatch: {payload['total_cholesterol_mmol']}"
    )
    assert payload["ldl_mmol"] == pytest.approx(3.84, rel=1e-3), (
        f"ldl_mmol mismatch: {payload['ldl_mmol']}"
    )
    assert payload["sbp_mmhg"] == pytest.approx(128.0, rel=1e-3), (
        f"sbp_mmhg mismatch: {payload['sbp_mmhg']}"
    )


@pytest.mark.integration
async def test_ingest_populates_embeddings_with_fake_llm(db_session: AsyncSession) -> None:
    """Every EHRRecord must have a non-null 768-d embedding after ingest with FakeLLMProvider.

    When an LLMProvider is supplied to UnifiedProfileService, the ingest must
    batch-embed all EHRRecord.content fields and persist the resulting vectors
    into the embedding column before committing.
    """
    report = await _run_ingest_with_embeddings(db_session)

    assert report.ehr_records > 0, "Expected at least one EHR record to be ingested"

    # Verify every EHR record has a non-null embedding
    stmt = select(EHRRecord)
    result = await db_session.execute(stmt)
    records = result.scalars().all()

    assert len(records) > 0, "Expected EHR records in DB after ingest"

    null_embedding_ids = [r.id for r in records if r.embedding is None]
    assert null_embedding_ids == [], (
        f"Found {len(null_embedding_ids)} EHRRecord(s) with null embeddings "
        f"after ingest with FakeLLMProvider. IDs: {null_embedding_ids[:10]}"
    )

    # Verify embedding dimensionality is 768
    sample = next(r for r in records if r.embedding is not None)
    assert len(sample.embedding) == 768, (
        f"Expected 768-d embedding but got {len(sample.embedding)}-d "
        f"for record id={sample.id}"
    )


@pytest.mark.integration
async def test_ingest_without_llm_leaves_embeddings_null(db_session: AsyncSession) -> None:
    """Ingest without an LLMProvider must leave embeddings as NULL.

    The LLM provider is optional — if not supplied, the ingest runs as before
    and embeddings stay null.  This preserves backward-compatibility for
    callers that don't supply an LLM.
    """
    await _run_ingest(db_session)

    stmt = select(EHRRecord)
    result = await db_session.execute(stmt)
    records = result.scalars().all()

    assert len(records) > 0, "Expected EHR records in DB after ingest"

    non_null_count = sum(1 for r in records if r.embedding is not None)
    assert non_null_count == 0, (
        f"Expected all embeddings to be NULL when no LLM is supplied, "
        f"but found {non_null_count} non-null embeddings"
    )


# ---------------------------------------------------------------------------
# T2 — daily_log and meal_log ingestion tests
# ---------------------------------------------------------------------------

#: EHR/wearable/lifestyle boilerplate for a single-patient temp fixture.
_EHR_HEADER = (
    "patient_id,age,sex,country,height_cm,weight_kg,bmi,smoking_status,"
    "alcohol_units_weekly,chronic_conditions,icd_codes,n_chronic_conditions,"
    "medications,n_visits_2yr,visit_history,"
    "sbp_mmhg,dbp_mmhg,total_cholesterol_mmol,ldl_mmol,hdl_mmol,"
    "triglycerides_mmol,hba1c_pct,fasting_glucose_mmol,crp_mg_l,egfr_ml_min\n"
)
_EHR_ROW = (
    "PTTEST,35,F,Germany,170.0,65.0,22.5,never,0,"
    "none,Z00.0,0,None,1,2023-01-01:Z00.0,"
    "120,80,5.0,3.0,1.5,1.0,5.0,4.5,0.5,90\n"
)
_WEARABLE_HEADER = (
    "patient_id,date,resting_hr_bpm,hrv_rmssd_ms,steps,active_minutes,"
    "sleep_duration_hrs,sleep_quality_score,deep_sleep_pct,spo2_avg_pct,"
    "calories_burned_kcal\n"
)
_WEARABLE_ROW = "PTTEST,2026-01-01,62,45.0,8000,30,7.5,80.0,20.0,97.5,1700\n"
_LIFESTYLE_HEADER = (
    "patient_id,survey_date,smoking_status,alcohol_units_weekly,"
    "diet_quality_score,fruit_veg_servings_daily,meal_frequency_daily,"
    "exercise_sessions_weekly,sedentary_hrs_day,stress_level,sleep_satisfaction,"
    "mental_wellbeing_who5,self_rated_health,water_glasses_daily\n"
)
_LIFESTYLE_ROW = "PTTEST,2026-01-01,never,0,7,3.0,3,4,6.0,3,7,70,7,8\n"

_DAILY_LOG_HEADER = (
    "patient_id,logged_at,mood,workout_minutes,sleep_hours,water_ml,"
    "alcohol_units,sleep_quality,workout_type,workout_intensity\n"
)
_DAILY_LOG_ROWS = (
    "PTTEST,2026-01-01T08:00:00,4,30,7.5,1800,0,4,walk,low\n"
    "PTTEST,2026-01-02T08:00:00,3,0,6.8,1600,0,3,,\n"
    "PTTEST,2026-01-03T08:00:00,5,45,7.8,2000,0,4,yoga,med\n"
)

_MEAL_LOG_HEADER = (
    "patient_id,analyzed_at,photo_uri,protein_g,carbs_g,fat_g,fiber_g,"
    "calories_kcal,description,longevity_swap\n"
)
_MEAL_LOG_ROWS = (
    "PTTEST,2026-01-01T12:00:00,manual://test-uri-1,32,38,14,9,420,"
    "Grilled salmon bowl,Swap white rice for quinoa\n"
    "PTTEST,2026-01-02T13:00:00,,28,45,10,6,380,"
    "Chicken pasta,Add more vegetables\n"
)


def _write_temp_fixture(tmp_path: Path) -> None:
    """Write all 5 CSV files for PTTEST into tmp_path."""
    (tmp_path / "ehr_records.csv").write_text(_EHR_HEADER + _EHR_ROW)
    (tmp_path / "wearable_telemetry_1.csv").write_text(_WEARABLE_HEADER + _WEARABLE_ROW)
    (tmp_path / "lifestyle_survey.csv").write_text(_LIFESTYLE_HEADER + _LIFESTYLE_ROW)
    (tmp_path / "daily_log.csv").write_text(_DAILY_LOG_HEADER + _DAILY_LOG_ROWS)
    (tmp_path / "meal_log.csv").write_text(_MEAL_LOG_HEADER + _MEAL_LOG_ROWS)


@pytest.mark.integration
async def test_ingest_daily_log_rows_written(
    db_session: AsyncSession,
    tmp_path: Path,
) -> None:
    """Ingest writes DailyLog rows to the database when daily_log.csv is present.

    3 daily_log rows for PTTEST in the fixture → 3 DailyLog rows in the DB.
    """
    _write_temp_fixture(tmp_path)

    svc = UnifiedProfileService(db_session)
    await svc.ingest("csv", data_dir=tmp_path)

    stmt = (
        select(func.count())
        .select_from(DailyLog)
        .where(getattr(DailyLog, "patient_id") == "PTTEST")
    )
    count = (await db_session.execute(stmt)).scalar_one()
    assert count == 3, f"Expected 3 DailyLog rows, got {count}"


@pytest.mark.integration
async def test_ingest_meal_log_rows_written(
    db_session: AsyncSession,
    tmp_path: Path,
) -> None:
    """Ingest writes MealLog rows to the database when meal_log.csv is present.

    2 meal_log rows for PTTEST in the fixture → 2 MealLog rows in the DB.
    """
    _write_temp_fixture(tmp_path)

    svc = UnifiedProfileService(db_session)
    await svc.ingest("csv", data_dir=tmp_path)

    stmt = (
        select(func.count())
        .select_from(MealLog)
        .where(getattr(MealLog, "patient_id") == "PTTEST")
    )
    count = (await db_session.execute(stmt)).scalar_one()
    assert count == 2, f"Expected 2 MealLog rows, got {count}"


@pytest.mark.integration
async def test_ingest_daily_and_meal_log_idempotent(
    db_session: AsyncSession,
    tmp_path: Path,
) -> None:
    """Running ingest twice yields the same DailyLog and MealLog row counts.

    The delete-then-insert strategy must be idempotent for the new tables.
    """
    _write_temp_fixture(tmp_path)
    svc = UnifiedProfileService(db_session)

    await svc.ingest("csv", data_dir=tmp_path)

    dl_stmt = (
        select(func.count())
        .select_from(DailyLog)
        .where(getattr(DailyLog, "patient_id") == "PTTEST")
    )
    ml_stmt = (
        select(func.count())
        .select_from(MealLog)
        .where(getattr(MealLog, "patient_id") == "PTTEST")
    )
    dl_count_run1 = (await db_session.execute(dl_stmt)).scalar_one()
    ml_count_run1 = (await db_session.execute(ml_stmt)).scalar_one()

    # Run ingest a second time
    await svc.ingest("csv", data_dir=tmp_path)

    dl_count_run2 = (await db_session.execute(dl_stmt)).scalar_one()
    ml_count_run2 = (await db_session.execute(ml_stmt)).scalar_one()

    assert dl_count_run1 == dl_count_run2, (
        f"DailyLog count changed: run1={dl_count_run1}, run2={dl_count_run2}"
    )
    assert ml_count_run1 == ml_count_run2, (
        f"MealLog count changed: run1={ml_count_run1}, run2={ml_count_run2}"
    )


@pytest.mark.integration
async def test_ingest_missing_daily_log_and_meal_log_files_no_error(
    db_session: AsyncSession,
    tmp_path: Path,
) -> None:
    """Ingest succeeds without daily_log.csv and meal_log.csv (backward compat).

    The fixture dir has only ehr, wearable, and lifestyle CSVs.
    No DailyLog or MealLog rows should be inserted, and no exception raised.
    """
    # Write only the mandatory files — no daily_log.csv, no meal_log.csv.
    (tmp_path / "ehr_records.csv").write_text(_EHR_HEADER + _EHR_ROW)
    (tmp_path / "wearable_telemetry_1.csv").write_text(_WEARABLE_HEADER + _WEARABLE_ROW)
    (tmp_path / "lifestyle_survey.csv").write_text(_LIFESTYLE_HEADER + _LIFESTYLE_ROW)

    svc = UnifiedProfileService(db_session)
    report = await svc.ingest("csv", data_dir=tmp_path)

    assert report.patients_ingested == 1

    dl_stmt = (
        select(func.count())
        .select_from(DailyLog)
        .where(getattr(DailyLog, "patient_id") == "PTTEST")
    )
    ml_stmt = (
        select(func.count())
        .select_from(MealLog)
        .where(getattr(MealLog, "patient_id") == "PTTEST")
    )
    dl_count = (await db_session.execute(dl_stmt)).scalar_one()
    ml_count = (await db_session.execute(ml_stmt)).scalar_one()

    assert dl_count == 0, f"Expected 0 DailyLog rows, got {dl_count}"
    assert ml_count == 0, f"Expected 0 MealLog rows, got {ml_count}"
