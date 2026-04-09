# 03 — System Architecture

High-level: **API-first backend, multi-platform clients, pluggable data sources, Gemini-powered AI layer, all on GCP.**

For locked versions see [04-tech-stack.md](04-tech-stack.md). For the adapter pattern in detail see [05-data-model.md](05-data-model.md). For AI specifics see [06-ai-layer.md](06-ai-layer.md).

## Component diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│                          CLIENTS (multi-OS)                         │
│                                                                      │
│  Next.js 15 PWA (web + installable iOS/Android/desktop)              │
│  └── optional Capacitor wrap → native iOS + Android binaries         │
│  Future: native Kotlin/Swift clients via same API                    │
└──────────────────────────────────────┬───────────────────────────────┘
                                       │ HTTPS + JSON (OpenAPI-typed)
                                       ▼
┌──────────────────────────────────────────────────────────────────────┐
│                     BACKEND (Cloud Run, Frankfurt)                  │
│                                                                      │
│   FastAPI + SQLModel + SQLAlchemy 2.0 async                          │
│                                                                      │
│   ┌─────────────────┐  ┌──────────────────┐  ┌───────────────────┐   │
│   │ Patient / EHR   │  │ AI Layer         │  │ Appointments       │  │
│   │ endpoints       │  │ (coach, RAG,     │  │ (in-network +      │  │
│   │                 │  │  analytics,      │  │  external booking) │  │
│   │                 │  │  notifications)  │  │                    │  │
│   └────────┬────────┘  └────────┬─────────┘  └────────┬──────────┘   │
│            │                    │                     │              │
│            ▼                    ▼                     ▼              │
│   ┌──────────────────────────────────────────────────────────────┐   │
│   │               Unified Patient Profile (service)              │   │
│   └──────────────────────────────┬───────────────────────────────┘   │
│                                  │                                   │
│   ┌──────────────────────────────▼───────────────────────────────┐   │
│   │                 Data Adapter Layer (Protocol)                │   │
│   │   CSV (today) │ FHIR │ Wearables │ Lab APIs │ Doctolib       │   │
│   └──────────────────────────────┬───────────────────────────────┘   │
└──────────────────────────────────┼───────────────────────────────────┘
                                   │
           ┌───────────────────────┼────────────────────────┐
           ▼                       ▼                        ▼
┌──────────────────────┐  ┌───────────────────┐  ┌─────────────────────┐
│  Cloud SQL Postgres  │  │  Vertex AI        │  │  Secret Manager     │
│  16 + pgvector       │  │  (Gemini 2.5)     │  │  (API keys, DB pw)  │
│  europe-west3 (FRA)  │  │                   │  │                     │
└──────────────────────┘  └───────────────────┘  └─────────────────────┘
```

## Request flow — two example paths

### Path A: "Show me my Vitality Score"
1. Client calls `GET /patients/me/vitality` with session token
2. FastAPI handler loads the unified patient profile via the data adapter layer
3. Score service computes composite (sleep + recovery + activity + biomarkers) from Postgres-stored unified data
4. Response typed via SQLModel / Pydantic v2 schema
5. Client renders score + trend chart

### Path B: "What did my last blood test say about cholesterol?" (the killer demo moment)
1. Client sends user question to `POST /coach/records-qa`
2. FastAPI embeds the query via `text-embedding-004` (Vertex AI)
3. pgvector HNSW index returns top-k relevant records (EHR notes, lab results) for **this patient only** (filtered by `patient_id` in SQL — hard isolation)
4. Gemini 2.5 Pro call with system prompt + retrieved context + safety framing
5. Response streams back with citations to the source record IDs
6. Client renders answer with clickable source links into the records view

## Deployment topology (demo day)

- **Region:** `europe-west3` (Frankfurt) for everything — EU data residency is a pitch talking point
- **Cloud Run** — FastAPI container, `python:3.12-slim` base, `--min-instances=1` to kill cold starts during the demo
- **Cloud SQL** — Postgres 16 + pgvector extension, db-f1-micro tier (plenty for hackathon)
- **Cloud SQL connector** (`cloud-sql-python-connector`) with asyncpg
- **Vertex AI** — Gemini + embeddings, same project, same region where possible
- **Secret Manager** — all API keys and DB credentials, mounted as env vars
- **Cloud Storage** (optional) — any generated artifacts (future-self visualizations, PDFs)

For frontend: deploy Next.js separately to **Cloud Run** (static export + edge caching) or **Vercel** if faster — doesn't matter for judging as long as the demo URL works.

## Security & isolation principles

Even for a hackathon, bake these in because they're pitch material:
- **Patient-scoped queries everywhere** — every SQL query filters by `patient_id`. No exception. RAG retrieval filters at the SQL level, not just post-hoc.
- **No PHI in LLM logs** — log request IDs, not patient data.
- **EU-region only** — no US sub-processors for PHI.
- **Explicit "not medical advice" framing** — bakes into every AI response.
- **Human-in-the-loop for clinical actions** — AI flags, doctor confirms.

See [08-legal-compliance.md](08-legal-compliance.md) for the legal rationale behind each of these.

## Why API-first matters for the pitch

*"We're not building 3 apps. We're building one API that powers every surface — web today, native iOS and Android next sprint, a clinician-facing dashboard for doctors after that, and eventually an insurer B2B2C portal. The data adapter layer means adding Apple Health or Doctolib is a day of work, not a month."*

That sentence is what judges want to hear. The architecture above makes it true.
