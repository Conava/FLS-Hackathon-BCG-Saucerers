# 03 — System Architecture

High-level: **API-first backend, multi-platform clients, pluggable data sources, Gemini-powered AI layer, all on GCP.**

> **Build status (manual trackers + protocol interactivity complete):** The full `/v1` backend API is shipped — 29 endpoints, LLM abstraction layer, pgvector RAG, SSE coach, protocol generator, meal vision, outlook engine, survey loop, self-tracking logs, manual tracker endpoints (sleep/water/workout, manual meal, protocol skip + reorder), and stub care-layer services. The committed `backend/openapi.json` is the authoritative contract; see `make openapi` to regenerate. The Next.js 15 PWA frontend is shipped at `frontend/` — all nine screens wired to the backend via the Route Handler proxy, with five BottomSheet tracker components and interactive protocol list.

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
1. Client calls `GET /v1/patients/{patient_id}/vitality` and `GET /v1/patients/{patient_id}/outlook` with the API key
2. FastAPI handler loads the unified patient profile via the data adapter layer
3. Score service computes the composite `VitalitySnapshot` across the four longevity dimensions (Biological Age, Sleep & Recovery, Cardiovascular Fitness, Lifestyle & Behavioral Risk)
4. Outlook service computes `VitalityOutlook` for 3/6/12 months from current streak state + active `ProtocolAction`s
5. Protocol service returns the active `Protocol` with today's `ProtocolAction`s + completion state from `DailyLog`
6. Response typed via SQLModel / Pydantic v2 schemas
7. Client renders score hero, outlook curve, streak counter, protocol list, and the nudge-of-the-day

### Path B: "What did my last blood test say about cholesterol?" (the killer Records moment)
1. Client sends user question to `POST /v1/patients/{patient_id}/records/qa`
2. FastAPI embeds the query via `text-embedding-004` (Vertex AI)
3. pgvector HNSW index returns top-k relevant records (EHR notes, lab results) for **this patient only** (filtered by `patient_id` in SQL — hard isolation)
4. Gemini 2.5 Pro call with `records-qa.system.md` (strict scope, citation-required) + retrieved records + user question
5. Response streams back with citations to the source record IDs
6. Client renders answer with clickable source links into the records view

### Path C: "Here's a photo of my lunch" (Nutrition woven-in)
1. Client uploads image to `POST /v1/patients/{patient_id}/meal-log` as `multipart/form-data`
2. FastAPI calls Gemini 2.5 Flash (vision) with `meal-vision.system.md`, passing the image and the patient's `LifestyleProfile.dietary_restrictions` + `known_allergies`
3. Model returns structured JSON (classification, macros, longevity swap, rationale) validated against `MealAnalysis`
4. Backend writes a `MealLog` row, updates today's protein/fiber rings, and flags protocol completion if a nutrition action matches
5. Client renders the classified meal, macro rings, and the one-line swap suggestion

### Path D: "Generate my weekly protocol" (Protocol Generator)
1. Client calls `POST /v1/patients/{patient_id}/protocol/generate` — triggered weekly, on survey retake, or on explicit user "re-plan"
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

## Frontend architecture

The `frontend/` directory is a self-contained Next.js 15 App Router application (pnpm, React 19, TypeScript strict, Tailwind v4 CSS-first).

### Route structure

```
src/app/
├── (auth)/
│   ├── login/          # Demo auth — email → httpOnly cookie
│   └── onboarding/     # Multi-step survey, GDPR consent
└── (app)/              # Shared layout with glass tab bar
    ├── today/          # Vitality ring, outlook curve, protocol (interactive: complete/skip/reorder), nudge, macro rings, quick-log sheets
    ├── coach/          # SSE streaming chat, suggested chips, AI disclosure
    ├── records/        # EHR list + plain-language Q&A with citations
    ├── insights/       # Longevity dimension signals, future-self simulator, risk flags
    ├── care/           # Appointments, three service pillars, clinician review, messages
    ├── meal-log/       # Photo upload → Gemini vision → macro analysis
    └── me/             # Profile, GDPR export/delete, data sources, consent
```

### Key design decisions

1. **Route Handler proxy** (`src/app/api/proxy/[...path]/route.ts`) — all browser → FastAPI traffic flows through a Next.js catch-all handler. The `patient_id` lives in an httpOnly cookie set at login and is injected into the `/v1/patients/{id}/…` path server-side. The browser never sees the patient identifier. The proxy streams response bodies through without buffering (critical for SSE).

2. **Demo auth** — `POST /api/auth/login` accepts an email address, looks it up in a hardcoded `DEMO_PATIENT_IDS` env-var map, and sets an httpOnly `patient_id` cookie. No passwords, no JWT. Middleware redirects unauthenticated requests to `/login`.

3. **Typed API client with Zod schemas** — `src/lib/api/client.ts` wraps all 29 endpoints. `src/lib/api/schemas.ts` holds hand-written Zod schemas derived from `backend/openapi.json`. All responses are runtime-validated at the trust boundary. Typed `ApiError` on failure.

4. **Manual service worker** (`public/sw.js`) — precaches the app shell and static assets. Explicitly bypasses `/api/proxy/*/coach/chat` and all POST/PUT/DELETE proxy requests to avoid breaking SSE and mutations. No `next-pwa` dependency.

5. **Server Components by default** — Today, Records, Insights, Care, Me do their initial data fetch on the server. Client Components are used only for interactive surfaces: vitality ring animation, SSE coach chat, future-self sliders, toggle lists, meal upload.

6. **Custom design system** — `src/components/design/` holds all project-specific components (VitalityRing, MacroRing, OutlookCurve, SignalCard, ProtocolCard, ChatBubble, AiDisclosureBanner, etc.). shadcn/ui primitives (Button, Card, Input, Badge, Dialog, Slider, etc.) live in `src/components/ui/` and are remapped to the project's `--color-*` tokens.

7. **Tracker sheets** — `src/components/trackers/` holds five BottomSheet client components: `QuickLogSleepSheet`, `QuickLogWaterSheet`, `QuickLogWorkoutSheet`, `QuickLogMealSheet`, `WeeklyCheckInSheet`. Each owns its own form state and submits via the proxy. `QuickLogGrid` in Today is state-driven (opens a sheet) rather than Link-based navigation. After any sheet submission, `router.refresh()` triggers a server re-fetch so vitality sub-scores, macro rings, and the protocol list reflect the new log.

### New backend endpoints (manual trackers + protocol interactivity)

Three endpoints added alongside the original 26:

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/v1/patients/{pid}/meal-log/manual` | Log a meal by macros without a photo. Body: `ManualMealLogIn`. Stores a row with `photo_uri = "manual://<uuid>"` and `classification = "manual"`. No LLM call. |
| `POST` | `/v1/patients/{pid}/protocol/skip-action` | Mark a protocol action as skipped today with a canned reason. Body: `{ action_id, reason }`. Sets `skipped_today = true`, `skip_reason`. Does not affect streak or outlook. |
| `POST` | `/v1/patients/{pid}/protocol/reorder` | Persist a new display order for the patient's protocol actions. Body: `{ action_ids: int[] }`. Writes `sort_order = index` for each. Subsequent `GET /protocol` returns actions ordered by `sort_order NULLS LAST, id ASC`. |

### New DB columns

Added as nullable columns (backwards-compatible — no migration required for existing rows):

| Table | Column | Type | Notes |
|---|---|---|---|
| `daily_log` | `sleep_quality` | `int \| None` | 1–5 Likert scale |
| `daily_log` | `workout_type` | `str \| None` | `walk\|run\|bike\|strength\|yoga\|other` |
| `daily_log` | `workout_intensity` | `str \| None` | `low\|med\|high` |
| `protocol_action` | `sort_order` | `int \| None` | Explicit display order; `NULLS LAST` in list query |
| `protocol_action` | `skipped_today` | `bool` | Default `false`; mirrors `completed_today` semantics |
| `protocol_action` | `skip_reason` | `str \| None` | Free-text canned reason stored on skip |

The `manual://` sentinel on `meal_log.photo_uri` signals manual entries to any reader that would otherwise try to render a photo — guard with `photo_uri.startsWith("manual://")`.

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
