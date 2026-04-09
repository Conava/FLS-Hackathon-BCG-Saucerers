# Longevity+

AI-driven longevity MVP for a European healthcare group — BCG Platinion AI Hackathon, Future Leader Summit Hamburg, 09–10.04.2026.

See [`docs/README.md`](docs/README.md) for the full documentation index. See [`mockup/index.html`](mockup/index.html) for the frontend contract.

## What's built

**Backend slice 1 — read API**
- Patients, vitality score, EHR records, wearable telemetry, insights, appointments, GDPR export
- Heuristic vitality engine across four longevity dimensions
- Pluggable `DataSource` Protocol with CSV adapter (1,000 synthetic patients)
- Hard `patient_id` isolation on every query via `PatientScopedRepository`
- API-key auth, JSON structured logging (PHI-free), request-ID middleware
- Docker Compose + Dockerfile + Cloud Run config, GitHub Actions CI

**Backend slice 2 — full `/v1` API**
- 26 endpoints across 15 routers — all Slice 1 paths moved under `/v1`
- LLM abstraction layer: `FakeLLMProvider` (dev/CI) + `GeminiProvider` (production via Vertex AI)
- File-loaded prompt system (`app/ai/prompts/*.system.md`) — editable without Python changes
- pgvector HNSW index; embeddings populated at ingest; RAG service for Records Q&A with citations
- SSE streaming coach (`text/event-stream`) with protocol-suggestion write-back
- Protocol generator (structured JSON output, 3–7 actions, constraint-validated)
- Meal vision (multimodal upload, `MealAnalysis`, macros, longevity swap)
- Outlook engine (streak math) + narrator (one-sentence LLM summary) + future-self simulator
- Survey loop: onboarding, weekly micro, quarterly deep retake
- Daily self-tracking: `DailyLog` (mood, workout, sleep, water, alcohol)
- Meal photo storage: local-fs (`./var/photos`) or GCS, wired into GDPR Art. 17 delete
- Stub care layer: notifications (LLM-generated copy), clinical review, referral, messages
- Committed `backend/openapi.json`; CI fails if spec drifts from code (`make openapi`)

**Frontend — not yet started.** See `mockup/index.html` for the UI contract.

## Quick start

Requires Docker and [`uv`](https://docs.astral.sh/uv/).

```bash
# Start Postgres (pgvector) + backend container
make up

# Seed the database with the provided CSV datasets
make seed

# Run the test suite
make test
```

The API is available at `http://localhost:8080`. OpenAPI docs at `http://localhost:8080/docs`.

All endpoints except `GET /healthz` require an `X-API-Key` header. Set the key via the `API_KEY` environment variable (default in docker-compose: `dev-api-key`).

### Without Docker (backend only)

```bash
cd backend
uv sync
# Start a local Postgres with pgvector first, then:
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
uv run python -m app.cli.ingest --source=csv --data-dir=../data
uv run pytest
```

## Repo layout

```
backend/        FastAPI backend — see backend/README.md for full detail
data/           Provided CSV datasets (ehr_records, wearable_telemetry, lifestyle_survey)
docs/           Project documentation — see docs/README.md
mockup/         Static HTML/CSS/JS frontend mockup (the UI contract)
cloudrun.yaml   Cloud Run service definition placeholder
docker-compose.yml
Makefile        up / down / seed / test / fmt / lint
```

## Documentation

- [`docs/README.md`](docs/README.md) — documentation index
- [`docs/04-tech-stack.md`](docs/04-tech-stack.md) — locked versions (read before writing code)
- [`docs/09-ai-assist-playbook.md`](docs/09-ai-assist-playbook.md) — AI-assistant hallucination traps for this stack
- [`backend/README.md`](backend/README.md) — backend commands, folder layout, API key setup
