# 04 — Tech Stack (LOCKED)

> **This file is the contract.** If you're generating code (human or AI), every version below is pinned. Deviations require a team decision and a doc update.

> **For AI assistants:** read this file before writing code. Many versions below have breaking changes from older patterns in your training data. See [09-ai-assist-playbook.md](09-ai-assist-playbook.md) for the specific traps.

## Summary

| Layer | Choice |
|---|---|
| **Frontend** | Next.js 15 + React 19 + Tailwind v4 + shadcn/ui + Zod, deployed as PWA (manual SW), optional Capacitor wrap |
| **Backend** | Python 3.12 + FastAPI + SQLModel + SQLAlchemy 2.0 async + asyncpg |
| **Database** | Cloud SQL Postgres 16 + pgvector (europe-west3) |
| **AI** | `google-genai` SDK → Gemini 2.5 Flash (coach, notifications) + 2.5 Pro (RAG, NL Q&A) + `text-embedding-004` |
| **Deploy** | Cloud Run (backend) + Cloud Run or Vercel (frontend) + Secret Manager + Cloud SQL connector |
| **Dev** | Docker Compose (pgvector/pgvector:pg16), `uv` for Python deps, pnpm for Node |

## Frontend

| Component | Version | Key notes |
|---|---|---|
| **Next.js** | **15** (App Router) | Server Components default. Use **Server Actions** for internal mutations, **Route Handlers** (`app/api/*/route.ts`) for calls to FastAPI. Note: `params` and `searchParams` are **async** in Next 15 — `const { id } = await params;` |
| **React** | **19** | |
| **Tailwind CSS** | **v4** | **Breaking:** NO `tailwind.config.js`. All config lives in `app/globals.css` via `@theme` directive. |
| **shadcn/ui** | latest | CLI initializes with Tailwind v4 + React 19 natively. Component source is copied into the repo, not imported. |
| **TypeScript** | 5.x strict | |
| **Package manager** | pnpm | Faster installs, better monorepo story if we grow |
| **Zod** | 3.x | Runtime schema validation for all API responses. Schemas in `src/lib/api/schemas.ts`. |
| **PWA** | Manual service worker + manifest (no `next-pwa`) | Installable on iOS Safari, Android Chrome, desktop. SW precaches app shell; bypasses SSE and mutation endpoints. |
| **Capacitor** (optional) | latest | Wrap the PWA into iOS/Android binaries if we want to demo on a physical device. ~1h of work. |

## Backend

| Component | Version | Key notes |
|---|---|---|
| **Python** | **3.12** | Not 3.13 — slightly better library compat. FastAPI 0.130+ requires 3.10 min. |
| **FastAPI** | latest (0.130+) | Auto-generates OpenAPI docs at `/docs` — great for the pitch. |
| **SQLModel** | latest | One class = DB model + API schema. Built on SQLAlchemy 2.0 + Pydantic v2. Always use `class X(SQLModel, table=True)` for tables. |
| **SQLAlchemy** | **2.0** async | Use `select()` + `session.execute()`, NOT legacy `session.query()`. Async sessions throughout. |
| **Pydantic** | **v2** | `model_config = ConfigDict(from_attributes=True)` — NOT the v1 `class Config: orm_mode = True`. |
| **asyncpg** | latest | Async Postgres driver, used under SQLAlchemy |
| **Uvicorn** | latest | ASGI server |
| **Gunicorn** | latest | Process manager in production, single Uvicorn worker per Cloud Run instance |
| **Dependency manager** | **`uv`** | 10–100× faster than pip, lockfile support, great for hackathons |

## Database

| Component | Version | Key notes |
|---|---|---|
| **Cloud SQL for PostgreSQL** | **16** | Smallest tier (`db-f1-micro`) — plenty for demo |
| **pgvector** | latest | `CREATE EXTENSION vector;` then `Column(Vector(768))` for embeddings. HNSW index for vector search. |
| **Region** | `europe-west3` (Frankfurt) | EU data residency — pitch talking point |
| **Connector** | `cloud-sql-python-connector` | Official Google connector, works with asyncpg |
| **Local dev** | `pgvector/pgvector:pg16` Docker image | Identical schema, switch via env var |

### pgvector operators (easy to get wrong)
- `<->` = L2 distance
- `<=>` = cosine distance ← **use this for text embeddings**
- `<#>` = inner product

HNSW index must match the operator used in queries:
```sql
CREATE INDEX ON docs USING hnsw (embedding vector_cosine_ops);
```

## AI Layer

| Component | Choice | Notes |
|---|---|---|
| **SDK** | **`google-genai`** | **IMPORTANT:** the old `vertexai.generative_models` is **deprecated June 2025, removed June 2026**. Do NOT use it. Do NOT use `google-generativeai` (different, older package). |
| **Mode** | `Client(vertexai=True, project=..., location="europe-west3")` | Routes through Vertex AI → billed to GCP credits |
| **Coach / notifications / analytics narration** | **Gemini 2.5 Flash** | $0.30 / $2.50 per M tokens, 1M context, fast |
| **NL record Q&A / complex reasoning** | **Gemini 2.5 Pro** | $1.00 / $10.00 per M tokens, 1M context, better reasoning |
| **Embeddings** | **`text-embedding-004`** | 768 dimensions — matches the `Vector(768)` column |
| **RAG framework** | **Roll our own** with `google-genai` + pgvector + raw SQL | LangChain/LlamaIndex are overkill for this scope and add a week of surface area. Direct SDK is <100 lines. |

## Deployment

| Component | Config |
|---|---|
| **Backend container** | `python:3.12-slim` base (NOT alpine — compat issues) |
| **ASGI** | Gunicorn + single Uvicorn worker (Cloud Run scales by instances, not workers) |
| **Port** | Must listen on `$PORT` (default 8080), not a hardcoded port |
| **Cold start** | `--min-instances=1` for demo day |
| **Concurrency** | Default 80 (I/O-bound, LLM-heavy → fine) |
| **Secrets** | Secret Manager, mounted as env vars via `--set-secrets` |
| **DB connection** | Cloud SQL connector, `--add-cloudsql-instances=PROJECT:europe-west3:longevity-db` |

## Dev environment

```bash
# Backend (via docker-compose — recommended)
make up        # starts db (pgvector/pgvector:pg16) + backend container
make seed      # ingest CSV datasets into Postgres
make test      # run pytest (testcontainers, no docker-compose dependency)

# Backend (directly, from backend/)
uv sync
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
uv run python -m app.cli.ingest --source=csv --data-dir=../data

# Frontend (from frontend/)
cd frontend
cp .env.example .env.local  # set BACKEND_URL + DEMO_PATIENT_IDS
pnpm install
pnpm dev
```

`docker-compose.yml` provides: `db` (pgvector/pgvector:pg16), `backend`, and optional `pgadmin` (profile-gated). An `.env` file in the repo root is loaded by the backend service for `API_KEY` and other settings.

## Why each choice (short form)

- **FastAPI over Node/Go:** Python has the densest LLM/AI ecosystem and the highest-quality AI-assistant code generation. For a 24h LLM-heavy build, this matters more than any framework benchmark.
- **SQLModel over split Pydantic/SQLAlchemy:** ~50% less boilerplate, built by the FastAPI author for this exact case. Still full SQLAlchemy power underneath.
- **Cloud SQL over AlloyDB:** AlloyDB is overkill for a hackathon; Cloud SQL + pgvector is the documented Google path and every tutorial uses it.
- **Gemini over Claude/OpenAI:** free GCP credits at the event.
- **Next.js PWA + Capacitor over React Native or KMP:** one codebase, every OS, works immediately, native wrapping is 1h when we want it. KMP/RN pay setup costs we can't afford in 24h.
- **Roll-our-own RAG over LangChain:** scope is small, direct SDK is clearer, LangChain surface area is a liability in a hackathon.

## Open questions

- Do we stand up a staging Cloud Run env or just go straight to prod for the demo?
- Do we use Vercel for frontend or Cloud Run everywhere for the "all GCP" pitch narrative?
