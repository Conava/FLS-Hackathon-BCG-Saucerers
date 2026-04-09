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
curl -H "X-API-Key: dev-api-key" http://localhost:8080/v1/patients/PT0001/profile
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

## Regenerate the OpenAPI spec

```bash
make openapi       # writes backend/openapi.json
```

CI fails if the committed spec is stale (`.github/workflows/backend-ci.yml`).

## Project layout

```
app/
  core/         config (pydantic-settings), JSON logging, request-ID middleware, API-key security
  db/           async engine, session factory, create_all (includes pgvector extension + HNSW index)
  models/       SQLModel table entities — Slice 1: Patient, EHRRecord, WearableDay, LifestyleProfile,
                VitalitySnapshot; Slice 2: Protocol, ProtocolAction, DailyLog, MealLog, SurveyResponse,
                VitalityOutlook, Message, Notification, ClinicalReview, Referral
  schemas/      Pydantic v2 request/response DTOs; AI responses include disclaimer + AIMeta
  repositories/ PatientScopedRepository base + concrete repos for all models
  adapters/     Pluggable DataSource Protocol + CSV adapter (see adapters/README.md);
                PhotoStorage Protocol + LocalFsPhotoStorage + GcsPhotoStorage
  ai/           LLMProvider Protocol, FakeLLMProvider, GeminiProvider, prompt_loader, prompts/
  services/     Vitality engine, RAG, coach (SSE), protocol generator, meal vision,
                outlook engine + narrator, future-self, notifications, clinical review,
                referral, messages, unified profile
  routers/      15 FastAPI routers mounted under /v1 (health stays at root)
  cli/          ingest CLI (app.cli.ingest), OpenAPI export CLI (app.cli.export_openapi)
tests/
  unit/         Pure logic, no DB (vitality engine, schemas, LLM fake, prompt loader, outlook math)
  integration/  Testcontainers Postgres + pgvector (repositories, routers, E2E, PHI-leak assertion)
```

## Routers (all endpoints)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/healthz` | Liveness probe (unauthenticated) |
| GET | `/v1/patients/{patient_id}` | Unified patient profile |
| GET | `/v1/patients/{patient_id}/vitality` | Heuristic vitality score + sub-scores |
| GET | `/v1/patients/{patient_id}/records` | EHR records (paginated) |
| GET | `/v1/patients/{patient_id}/records/{record_id}` | Single EHR record |
| GET | `/v1/patients/{patient_id}/wearable` | Wearable telemetry series |
| GET | `/v1/patients/{patient_id}/insights` | Wellness flags |
| GET, POST | `/v1/patients/{patient_id}/appointments/` | Appointments list + booking |
| GET | `/v1/patients/{patient_id}/gdpr/export` | GDPR Art. 15 data export |
| DELETE | `/v1/patients/{patient_id}/gdpr/` | GDPR Art. 17 erasure (deletes all rows + photo files) |
| POST | `/v1/patients/{patient_id}/records/qa` | RAG Records Q&A with citations |
| POST | `/v1/patients/{patient_id}/coach/chat` | SSE streaming coach (`text/event-stream`) |
| POST | `/v1/patients/{patient_id}/protocol/generate` | Generate weekly protocol via LLM |
| GET | `/v1/patients/{patient_id}/protocol` | Get active protocol + actions |
| POST | `/v1/patients/{patient_id}/protocol/complete-action` | Mark action complete, update streak |
| POST, GET | `/v1/patients/{patient_id}/survey` | Submit survey (onboarding/weekly/quarterly) |
| GET | `/v1/patients/{patient_id}/survey/history` | Survey history by kind |
| POST, GET | `/v1/patients/{patient_id}/daily-log` | Log daily check-in / get history |
| POST, GET | `/v1/patients/{patient_id}/meal-log` | Upload meal photo + get history |
| POST | `/v1/patients/{patient_id}/insights/outlook-narrator` | LLM outlook narrative |
| POST | `/v1/patients/{patient_id}/insights/future-self` | Future-self projection |
| GET | `/v1/patients/{patient_id}/outlook` | Current VitalityOutlook |
| POST | `/v1/patients/{patient_id}/notifications/smart` | Generate smart notification copy |
| GET, POST | `/v1/patients/{patient_id}/clinical-review` | Clinical review stub |
| GET, POST | `/v1/patients/{patient_id}/referral` | Referral stub |
| GET, POST | `/v1/patients/{patient_id}/messages` | Messages to care team |

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | *(required)* | Async SQLAlchemy DSN: `postgresql+asyncpg://user:pass@host/db` |
| `API_KEY` | *(required)* | Shared secret sent in `X-API-Key` header |
| `APP_ENV` | `development` | `development` \| `production` |
| `LOG_LEVEL` | `INFO` | Python log level |
| `LLM_PROVIDER` | `fake` | `fake` (deterministic, no network) \| `gemini` (Vertex AI) |
| `GCP_PROJECT` | `None` | GCP project ID — required when `LLM_PROVIDER=gemini` |
| `GCP_LOCATION` | `europe-west3` | GCP region for Vertex AI (EU data-residency) |
| `PHOTO_STORAGE_BACKEND` | `local` | `local` (writes to `PHOTO_LOCAL_DIR`) \| `gcs` |
| `PHOTO_LOCAL_DIR` | `./var/photos` | Root directory for local photo storage |
| `PHOTO_GCS_BUCKET` | `None` | GCS bucket name — required when `PHOTO_STORAGE_BACKEND=gcs` |
