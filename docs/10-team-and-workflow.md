# 10 — Team & Workflow

6 people, 24 hours, one working MVP + one pitch. This doc is the coordination contract.

## Pod structure

| Pod | People | Primary ownership | Dependencies |
|---|---|---|---|
| **Strategy & Pitch** | 1 | Persona, journey, slide deck, demo script, rehearsal. Copy review of all AI prompts for wellness framing. | Inputs from every other pod by hour 20 |
| **Backend Core** | 2 | FastAPI scaffolding, SQLModel schemas, data adapter layer, Postgres + pgvector, unified patient profile, Cloud Run deploy | Hour 0 kickoff, unblocks AI + Frontend by hour 6 |
| **AI Layer** | 1 | `google-genai` integration, coach, NL record RAG, notifications, analytics narration, future-self simulator. Prompt files in `app/ai/prompts/`. | Needs adapter loading by hour 6 |
| **Frontend** | 2 | Next.js 15 PWA, Tailwind v4 setup, shadcn scaffolding, all screens from the demo flow, Capacitor wrap if time permits | Can scaffold UI with mocks hours 0–6, switch to real API hours 6+ |

Everyone uses Claude Code / Gemini Code Assist as a pair programmer. [09-ai-assist-playbook.md](09-ai-assist-playbook.md) is required reading for all devs before writing a line.

## 24-hour timeline (target)

| Hours | Phase | Everyone does |
|---|---|---|
| **0–2** | **Alignment** | Read docs/01, 02, 03, 04, 07 together. Dataset exploration complete. Persona + journey locked via `/devline:brainstorm`. Pod assignments finalized. Repo scaffolded. |
| **2–6** | **Scaffolding** | Backend: FastAPI + SQLModel + CSV adapter running locally. Frontend: Next.js 15 + Tailwind v4 + shadcn, dashboard screen with mock data. AI: Gemini client working, first prompt hitting the API. Strategy: slide skeleton + persona slide done. |
| **6–14** | **Core build** | Backend: all endpoints, pgvector indexing, deploy to Cloud Run with `--min-instances=1`. Frontend: all demo-flow screens wired to real API. AI: coach + RAG + one more capability working. Strategy: slides 60% done. |
| **14–20** | **Integration + polish** | End-to-end demo flow works. Bugs fixed. Styling polished. Notifications + risk flags + commercial touchpoints wired. Strategy: slides final. |
| **20–22** | **Nice-to-haves** | Future-self simulator. Capacitor wrap. Whatever extra we can ship. |
| **22–24** | **Rehearsal + contingencies** | Demo rehearsed ≥3 times. Fallback video recorded. Everyone knows their 30 seconds on stage. |

**Protected: last 2 hours are frozen.** No new features after hour 22. If it's not working by then, cut it.

## Git workflow

- Branch: `main` is the demo branch. Protected.
- Feature branches: `pod/<pod>-<feature>` (e.g. `backend-csv-adapter`, `frontend-coach-ui`)
- PRs: lightweight. Review = "does it run + does the demo still work?" — not style nitpicks in a 24h sprint.
- Merge often. Small PRs. Minimize conflict surface.

## Repo layout (target)

```
/
├── CLAUDE.md                  # AI assistant entry point — references docs/04 + docs/09
├── README.md                  # quick-start: clone, uv sync, docker compose up, pnpm dev
├── docker-compose.yml         # local dev: pgvector + backend + frontend
│
├── docs/                      # this directory — see docs/README.md
│
├── data/                      # provided CSVs (gitignored if large)
│
├── backend/
│   ├── pyproject.toml         # uv-managed
│   ├── Dockerfile             # python:3.12-slim, gunicorn + uvicorn
│   ├── app/
│   │   ├── main.py            # FastAPI app + lifespan
│   │   ├── config.py          # settings via pydantic-settings
│   │   ├── db.py              # async engine + session
│   │   ├── models/            # SQLModel tables
│   │   ├── schemas/            # Pydantic schemas where they diverge from tables
│   │   ├── routers/           # FastAPI endpoints
│   │   ├── services/          # business logic (vitality score, etc.)
│   │   ├── adapters/          # DataSource implementations
│   │   │   ├── base.py
│   │   │   └── csv_source.py
│   │   └── ai/
│   │       ├── client.py      # google-genai Client setup
│   │       ├── coach.py
│   │       ├── rag.py
│   │       └── prompts/       # versioned prompt .md files
│   └── tests/
│
├── frontend/
│   ├── package.json           # pnpm-managed
│   ├── next.config.ts
│   ├── app/
│   │   ├── globals.css        # Tailwind v4 @theme config
│   │   ├── layout.tsx
│   │   ├── page.tsx           # dashboard
│   │   ├── coach/page.tsx
│   │   ├── records/page.tsx
│   │   ├── appointments/page.tsx
│   │   └── ...
│   ├── components/
│   │   └── ui/                # shadcn components (copied in)
│   └── lib/
│       └── api.ts             # typed FastAPI client
│
└── infra/
    ├── cloudrun.sh            # gcloud run deploy commands
    └── schema.sql             # pgvector extension + index
```

## Communication cadence

- **Hour 0:** 30-min kickoff, everyone reads docs/01–04
- **Every 4 hours:** 10-min standup — blockers only
- **Hour 20:** full demo walkthrough, identify gaps
- **Hour 22:** freeze + rehearsal loop

## Definition of done for the demo

- [ ] Anna account loads in <2s on Cloud Run demo URL
- [ ] Vitality Score shows real computed value from CSV data
- [ ] Coach responds in <5s (streamed) with a citation from Anna's real records
- [ ] NL record Q&A returns a correct answer with clickable citation
- [ ] Risk flag surfaces → diagnostic package card → mocked booking works
- [ ] At least one "wow" feature built (future-self simulator OR polished Capacitor native wrap)
- [ ] Pitch deck complete, rehearsed 3× under 3 minutes
- [ ] Fallback video recorded for wifi-disaster scenario
- [ ] Legal compliance slide in the deck
- [ ] Architecture slide in the deck

## Open questions

- Who owns the demo-day laptop/phone setup?
- Do we do a hard rotation at hour 12 for sleep, or rolling power naps?
