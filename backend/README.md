# Longevity+ Backend

FastAPI + SQLModel + SQLAlchemy 2.0 async + Postgres 16 + pgvector.

Every SQL query is `patient_id`-scoped by the base repository (`PatientScopedRepository`) — GDPR isolation is enforced in code, not by convention.

## Prerequisites

- Python 3.12 (pinned in `.python-version`)
- [`uv`](https://docs.astral.sh/uv/) — `curl -LsSf https://astral.sh/uv/install.sh | sh`
- Docker (for local Postgres via `docker-compose`)

## Run locally

```bash
# 1. Install dependencies
uv sync

# 2. Start Postgres with pgvector (from repo root)
docker compose up -d db

# 3. Start the backend (from repo root)
docker compose up -d backend
# or run directly:
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8080

# 4. Seed the database with the provided CSV datasets
uv run python -m app.cli.ingest --source=csv --data-dir=../data
```

Use `make up && make seed` from the repo root for the same effect.

## API key

All endpoints except `GET /healthz` require an `X-API-Key` header. Set the key via the `API_KEY` environment variable. The docker-compose default is `dev-api-key`.

```bash
curl -H "X-API-Key: dev-api-key" http://localhost:8080/patients/PT0001/profile
```

OpenAPI docs (unauthenticated) at `http://localhost:8080/docs`.

## Run tests

```bash
uv run pytest
```

Integration tests spin up a throwaway Postgres via Testcontainers. Tests that require a live docker-compose stack are gated behind the `compose` marker and excluded by default (`addopts = "-m 'not compose'"`).

## Lint and type-check

```bash
uv run ruff check app    # lint
uv run ruff format app   # format
uv run mypy app          # type-check (strict)
```

Or via Makefile: `make lint`, `make fmt`.

## Project layout

```
app/
  core/         config (pydantic-settings), JSON logging, request-ID middleware, API-key security
  db/           async engine, session factory (get_session dependency)
  models/       SQLModel table entities (Patient, EHRRecord, WearableDay, LifestyleProfile, VitalitySnapshot)
  schemas/      Pydantic v2 response DTOs (wellness-framed copy, separate from table models)
  repositories/ PatientScopedRepository base + concrete repos (patient, ehr, wearable, vitality)
  adapters/     Pluggable DataSource Protocol + CSV adapter — see adapters/README.md
  services/     Vitality engine, insights derivation, UnifiedProfileService (ingest orchestration)
  routers/      FastAPI routers: health, patients, appointments, gdpr
  cli/          ingest CLI (app.cli.ingest)
tests/
  unit/         Pure logic, no DB (vitality engine, schema validation)
  integration/  Testcontainers Postgres (repository, router, E2E auth)
```

## Routers shipped (slice 1 — read-only)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/healthz` | Liveness probe (unauthenticated) |
| GET | `/patients/{patient_id}/profile` | Unified patient profile |
| GET | `/patients/{patient_id}/vitality` | Heuristic vitality score + sub-scores |
| GET | `/patients/{patient_id}/records` | EHR records (paginated) |
| GET | `/patients/{patient_id}/wearable` | Wearable telemetry series |
| GET | `/patients/{patient_id}/insights` | Wellness flags derived from vitality result |
| GET | `/patients/{patient_id}/appointments` | Appointment stubs |
| GET | `/patients/{patient_id}/gdpr/export` | GDPR Art. 15 data export |
| DELETE | `/patients/{patient_id}/gdpr` | GDPR Art. 17 erasure request (stub — schedules, does not delete) |

AI layer endpoints (coach, records Q&A, protocol generation, meal vision) are slice 2.

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://postgres:dev@localhost:5432/longevity` | Async SQLAlchemy connection string |
| `API_KEY` | *(required)* | Shared-secret key sent in `X-API-Key` header |
| `APP_ENV` | `development` | `development` \| `production` |
| `LOG_LEVEL` | `INFO` | Python log level |
