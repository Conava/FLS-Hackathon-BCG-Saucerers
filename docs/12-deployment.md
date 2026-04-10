# 12 — Deployment Guide

> **Status:** live. Backend and frontend deployed to Cloud Run in `europe-west3`. Database on Cloud SQL. AI via Gemini API key (AI Studio).

## Architecture overview

```
Browser → Cloud Run (frontend, port 3000)
             ↓ Route Handler proxy injects X-API-Key + patient_id
         Cloud Run (backend, port 8080)
             ↓ asyncpg over unix socket
         Cloud SQL (Postgres 16 + pgvector)
             ↓ google-genai SDK
         Gemini 2.5 (via API key)
```

Everything runs in **europe-west3 (Frankfurt)** for EU data residency.

## GCP project

- Project ID: `ai-hack26ham-445`
- All resources (Cloud Run, Cloud SQL, Secret Manager, Artifact Registry) live in this project.

## What was set up

### Cloud SQL
- Instance: `longevity-db` (Postgres 16, db-f1-micro, europe-west3)
- Database: `longevity`
- pgvector extension enabled (`CREATE EXTENSION IF NOT EXISTS vector;`)
- Connection name: `ai-hack26ham-445:europe-west3:longevity-db`

### Secret Manager
Three secrets, all in europe-west3:

| Secret name | What it holds | Used by |
|---|---|---|
| `api-key` | Shared API key for backend ↔ frontend auth | Backend (`API_KEY`), Frontend (`BACKEND_API_KEY`) |
| `gemini-api-key` | Gemini API key from AI Studio | Backend (`GEMINI_API_KEY`) |
| `db-password` | Cloud SQL postgres password | Referenced in `DATABASE_URL` env var |

### Cloud Run — backend (`longevity-backend`)
- Source: GitHub repo, `backend/Dockerfile`, built via Cloud Build
- Build context is the **repo root** (not `backend/`) because the Dockerfile copies `data/` from the repo root
- Port: 8080
- Min instances: 1

Env vars:
```
APP_ENV=production
LOG_LEVEL=INFO
LLM_PROVIDER=gemini
PHOTO_STORAGE_BACKEND=local
DATABASE_URL=postgresql+asyncpg://postgres:<password>@/longevity?host=/cloudsql/ai-hack26ham-445:europe-west3:longevity-db
```

Secrets (env var name → secret reference):
```
API_KEY          ← api-key:latest
GEMINI_API_KEY   ← gemini-api-key:latest
```

Cloud SQL connection: `ai-hack26ham-445:europe-west3:longevity-db` (added in the Connections tab).

### Cloud Run — frontend (`longevity-frontend`)
- Source: GitHub repo, `frontend/Dockerfile`, built via Cloud Build
- Port: **3000** (not 8080)
- Min instances: 1

Env vars:
```
NODE_ENV=production
BACKEND_URL=https://longevity-backend-743247495674.europe-west3.run.app
DEMO_PATIENT_IDS=rebecca@demo.com:PT0199,pt0421@demo.com:PT0421
```

Secrets:
```
BACKEND_API_KEY  ← api-key:latest
```

## Seeding the database

The CSV seed data (`data/ehr_records.csv`, `data/wearable_data.csv`, `data/lifestyle_survey.csv`) is baked into the backend Docker image. Two admin endpoints handle seeding:

```bash
# First-time seed (idempotent)
curl -X POST https://longevity-backend-743247495674.europe-west3.run.app/v1/admin/seed \
  -H "X-API-Key: <API_KEY_VALUE>"

# Nuke everything and reseed (for demo resets)
curl -X POST https://longevity-backend-743247495674.europe-west3.run.app/v1/admin/reseed \
  -H "X-API-Key: <API_KEY_VALUE>"
```

Replace `<API_KEY_VALUE>` with the actual value stored in the `api-key` secret.

## How to rotate / change the API key

1. Console → **Secret Manager** → `api-key` → **New version** → paste new value → **Add new version** → disable the old version
2. Console → **Cloud Run** → `longevity-backend` → **Edit & Deploy New Revision** → no changes needed, just deploy (it references `latest`)
3. Do the same for `longevity-frontend`
4. Both services will pick up the new secret on the next revision

The API key must match between backend (`API_KEY`) and frontend (`BACKEND_API_KEY`) — they reference the same secret.

## How to rotate / change the Gemini API key

1. Console → **Secret Manager** → `gemini-api-key` → **New version** → paste new key → disable old version
2. Console → **Cloud Run** → `longevity-backend` → **Edit & Deploy New Revision** → deploy

Frontend doesn't use the Gemini key — only the backend does.

## Switching AI providers

The backend has a pluggable LLM abstraction layer in `backend/app/ai/llm.py`. Three modes:

### Current: Gemini via API key (AI Studio)
```
LLM_PROVIDER=gemini
GEMINI_API_KEY=<your-key>
```
Uses `genai.Client(api_key=...)`. No GCP IAM needed.

### Alternative: Gemini via Vertex AI (service account)
```
LLM_PROVIDER=gemini
GCP_PROJECT=ai-hack26ham-445
GCP_LOCATION=europe-west3
```
Remove `GEMINI_API_KEY`. Uses `genai.Client(vertexai=True, ...)` with Application Default Credentials from the Cloud Run service account. Requires `roles/aiplatform.user` on the service account.

### Development: Fake provider (no network)
```
LLM_PROVIDER=fake
```
Returns deterministic stub responses. No API key needed. Used for tests and local dev.

### Adding a new provider
1. Create a new class in `backend/app/ai/llm.py` implementing the `LLMProvider` protocol (4 methods: `generate`, `generate_stream`, `embed`, `generate_vision`)
2. Add a new branch in `get_llm_provider()` at the bottom of the same file
3. Add any new settings fields to `backend/app/core/config.py`
4. Set `LLM_PROVIDER=<your-new-name>` in the Cloud Run env vars

The protocol is defined at line ~44 of `llm.py`. All four methods are async. `generate` returns text or structured JSON, `generate_stream` returns an async iterator, `embed` returns float vectors, `generate_vision` accepts image bytes and returns structured JSON.

## Common issues

| Symptom | Cause | Fix |
|---|---|---|
| Container fails health probe, no logs | Required env var missing (`API_KEY`, `DATABASE_URL`) | Check Variables & Secrets in the revision — env var names must use underscores |
| Secret resolves to empty | Service account missing Secret Manager Secret Accessor role | IAM → add the role to the Compute Engine default SA |
| `?host=/cloudsql/...` connection refused | Cloud SQL connection not added | Revision → Connections tab → Add Cloud SQL connection |
| Fake responses from coach ("Here is a reply.") | `LLM_PROVIDER=fake` or `GEMINI_API_KEY` empty | Set `LLM_PROVIDER=gemini` and verify the secret is populated |
| Seed returns 503 "data directory not found" | Old image without `data/` baked in | Rebuild — the Dockerfile now copies `data/` from repo root |

## Redeploying after code changes

Push to the branch connected in Cloud Build. Both services are set to **continuous deployment** — they rebuild and redeploy automatically on push. If you need a manual redeploy: Cloud Run → service → **Edit & Deploy New Revision** → Deploy.

If you change `backend/openapi.json`-affecting routes, run `make openapi` locally and commit the updated file — the pre-commit hook checks for drift.
