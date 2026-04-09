# 03 — System Architecture

High-level: **API-first backend, multi-platform clients, pluggable data sources, Gemini-powered AI layer, all on GCP.**

> **Build status (slice 1 complete):** The backend read API, data adapter layer, vitality engine, and all repos are shipped. The AI Layer component (coach, RAG, embeddings, protocol generation) is the slice-2 target.

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
│   │ Patient / EHR   │  │ AI Layer         │  │ Care                │  │
│   │ + Records Q&A   │  │ coach, records-  │  │ clinics /           │  │
│   │                 │  │ qa, protocol-gen,│  │ diagnostics /       │  │
│   │                 │  │ meal-vision,     │  │ home care           │  │
│   │                 │  │ outlook, notif   │  │                     │  │
│   └────────┬────────┘  └────────┬─────────┘  └────────┬──────────┘   │
│            │                    │                     │              │
│            │   ┌────────────────┴──────────────────┐  │              │
│            │   │  Protocol + Streak engine         │  │              │
│            │   │  (Today, DailyLog, MealLog,       │  │              │
│            │   │   VitalityOutlook, Survey loop)   │  │              │
│            │   └────────────────┬──────────────────┘  │              │
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

## Request flow — four example paths

### Path A: "Show me my Today" (Score + Outlook + Protocol)
1. Client calls `GET /patients/me/today` with session token
2. FastAPI handler loads the unified patient profile via the data adapter layer
3. Score service computes the composite `VitalitySnapshot` across the four longevity dimensions (Biological Age, Sleep & Recovery, Cardiovascular Fitness, Lifestyle & Behavioral Risk)
4. Outlook service computes `VitalityOutlook` for 3/6/12 months from current streak state + active `ProtocolAction`s
5. Protocol service returns the active `Protocol` with today's `ProtocolAction`s + completion state from `DailyLog`
6. Response typed via SQLModel / Pydantic v2 schemas
7. Client renders score hero, outlook curve, streak counter, protocol list, and the nudge-of-the-day

### Path B: "What did my last blood test say about cholesterol?" (the killer Records moment)
1. Client sends user question to `POST /records/qa`
2. FastAPI embeds the query via `text-embedding-004` (Vertex AI)
3. pgvector HNSW index returns top-k relevant records (EHR notes, lab results) for **this patient only** (filtered by `patient_id` in SQL — hard isolation)
4. Gemini 2.5 Pro call with `records-qa.system.md` (strict scope, citation-required) + retrieved records + user question
5. Response streams back with citations to the source record IDs
6. Client renders answer with clickable source links into the records view

### Path C: "Here's a photo of my lunch" (Nutrition woven-in)
1. Client uploads image to `POST /today/meal-log` with the patient session
2. FastAPI calls Gemini 2.5 Flash (vision) with `meal-vision.system.md`, passing the image and the patient's `LifestyleProfile.dietary_restrictions` + `known_allergies`
3. Model returns structured JSON (classification, macros, longevity swap, rationale) validated against `MealAnalysis`
4. Backend writes a `MealLog` row, updates today's protein/fiber rings, and flags protocol completion if a nutrition action matches
5. Client renders the classified meal, macro rings, and the one-line swap suggestion

### Path D: "Generate my weekly protocol" (Protocol Generator)
1. Client calls `POST /protocol/generate` — triggered weekly, on survey retake, or on explicit user "re-plan"
2. FastAPI gathers the inputs: `LifestyleProfile` (with hard constraints: time budget, out-of-pocket budget, allergies, restrictions), latest `VitalitySnapshot`, recent 7-day wearable summary, last-week adherence from `DailyLog`
3. Gemini 2.5 Pro call with `protocol-generator.system.md`, structured-output mode enforcing `GeneratedProtocol`
4. Backend validates the JSON, retires the prior `Protocol` (sets `is_active=false`), inserts new `Protocol` + `ProtocolAction` rows
5. Client refreshes Today with the new protocol and Coach's one-paragraph rationale

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
