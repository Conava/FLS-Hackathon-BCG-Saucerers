# 09 — AI-Assist Playbook

How to get Claude Code, Gemini Code Assist, and Codex to write **correct** code on this stack. Most completions for this stack look right but silently use outdated or wrong patterns. This doc lists the traps and how to pre-empt them.

> **For AI assistants reading this file:** use it as your ground truth for this repo's conventions. The version pins in [04-tech-stack.md](04-tech-stack.md) override any patterns you might default to from training data.

## The golden rule

**Pin the stack in every non-trivial prompt.** A one-line preamble cuts hallucinations dramatically:

> *"Stack: FastAPI + SQLModel + SQLAlchemy 2.0 async + Pydantic v2 + `google-genai` SDK (not google-generativeai, not vertexai.generative_models) + Next.js 15 App Router + Tailwind v4 (no tailwind.config.js). See docs/04-tech-stack.md."*

Drop it into your prompt. Every time. It's annoying and it works.

## The traps, ranked by how much time they'll cost you

### 1. Gemini SDK package name (silent 30-minute trap)
**Wrong — all in training data, all broken:**
```python
import google.generativeai as genai          # OLD package
from vertexai.generative_models import ...   # DEPRECATED June 2025, removed June 2026
from vertexai.preview.generative_models import ...  # DEPRECATED
```

**Right:**
```python
from google import genai
client = genai.Client(vertexai=True, project="...", location="europe-west3")
```

**How to prompt:** *"Use the `google-genai` package. Do not use `google-generativeai` or `vertexai.generative_models`."*

### 2. Pydantic v2 config
**Wrong (v1 syntax, shows up silently):**
```python
class PatientRead(BaseModel):
    class Config:
        orm_mode = True
```

**Right (v2):**
```python
from pydantic import BaseModel, ConfigDict
class PatientRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
```

**How to prompt:** *"Pydantic v2 syntax — use `model_config = ConfigDict(...)`, not `class Config`."*

### 3. SQLAlchemy 1.x vs 2.0
**Wrong (1.x legacy):**
```python
patients = session.query(Patient).filter(Patient.id == pid).all()
```

**Right (2.0):**
```python
from sqlalchemy import select
result = await session.execute(select(Patient).where(Patient.id == pid))
patients = result.scalars().all()
```

**How to prompt:** *"SQLAlchemy 2.0 style, async. Use `select()` and `session.execute()`. Never `session.query()`."*

### 4. SQLModel vs raw SQLAlchemy
Assistants default to raw SQLAlchemy because it has more training data. We use SQLModel.

**How to prompt:** *"Use SQLModel with `class X(SQLModel, table=True)`. Don't generate separate SQLAlchemy + Pydantic classes."*

### 5. Tailwind v4 has no config file
Assistants will create a `tailwind.config.js` or `tailwind.config.ts`. **Delete it immediately.** Tailwind v4 config lives in your CSS:

```css
/* app/globals.css */
@import "tailwindcss";

@theme {
  --color-brand: #14b8a6;
  --font-sans: "Inter", sans-serif;
}
```

**How to prompt:** *"Tailwind v4 — CSS-first config via `@theme` directive in `app/globals.css`. Do not create a `tailwind.config.js`."*

### 6. Next.js 15 async params
Assistants still write Next 14 sync-params code.

**Wrong (v14):**
```tsx
export default function Page({ params }: { params: { id: string } }) {
  const { id } = params;
}
```

**Right (v15):**
```tsx
export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
}
```

**How to prompt:** *"Next.js 15 — `params` and `searchParams` are async. Await them."*

### 7. Server Actions vs Route Handlers vs a fake API
Assistants sometimes invent a Next.js API layer in `app/api/*` that just proxies to FastAPI. Don't. The real backend is FastAPI. In the frontend:

- **Server Actions** (`"use server"`) — for internal form mutations that don't need FastAPI
- **Route Handlers** (`app/api/*/route.ts`) — only if we need a BFF layer; otherwise call FastAPI directly from Server Components or Client Components

**How to prompt:** *"Call the FastAPI backend directly from Server Components via `fetch`. Don't create a BFF in `app/api/`."*

### 8. pgvector operators
Three different distance operators, assistants mix them up.

- `<->` = L2 distance
- `<=>` = **cosine** (use this for text embeddings)
- `<#>` = inner product

Index must match the operator used in queries:
```sql
CREATE INDEX ON ehr_records USING hnsw (embedding vector_cosine_ops);
-- then query with <=>
```

**How to prompt:** *"pgvector cosine distance — `<=>` operator, `vector_cosine_ops` index. Don't use `<->`."*

### 9. Cloud Run port + lifespan
Must listen on `$PORT` (default 8080). Hardcoded `8000` = cold-start failure.

```python
# Dockerfile CMD
exec gunicorn -k uvicorn.workers.UvicornWorker \
  --bind :$PORT --workers 1 --timeout 120 app.main:app
```

**How to prompt:** *"Listen on `$PORT` env var with default 8080. Single Uvicorn worker per Cloud Run instance."*

### 10. Secrets in example `.env` files
Assistants will put `GEMINI_API_KEY="AIza..."` in `.env.example`. **Never commit real keys.** Only placeholder values:

```
# .env.example
GOOGLE_CLOUD_PROJECT=your-project
GOOGLE_CLOUD_LOCATION=europe-west3
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/longevity
```

Real keys → Secret Manager + `--set-secrets` flag on `gcloud run deploy`.

### 11. `uv` over `pip`
We use [`uv`](https://docs.astral.sh/uv/) for Python deps. It's ~100× faster and has proper lockfiles. Assistants default to pip.

```bash
uv init
uv add fastapi sqlmodel 'sqlalchemy[asyncio]' asyncpg pgvector google-genai
uv run fastapi dev app/main.py
```

**How to prompt:** *"Use `uv` for Python dependency management, not pip or poetry."*

### 12. Docker base image
`python:3.12-slim` is the sweet spot. NOT alpine (compat issues with binary wheels). NOT the full `python:3.12` (huge).

## Prompt templates that work well

### For a new backend endpoint
> *"Add a FastAPI endpoint `GET /patients/me/vitality` that returns the latest VitalitySnapshot. Stack: FastAPI + SQLModel + SQLAlchemy 2.0 async. Pydantic v2 response model. Filter by `patient_id` from the session. Use `select()` + `session.execute()`. Follow patterns in `app/routers/patients.py`."*

### For a new frontend screen
> *"Build a Next.js 15 App Router page at `app/coach/page.tsx`. Server Component that fetches from `${process.env.API_URL}/coach/history` and renders a chat UI. Use shadcn/ui `Card`, `Button`, `ScrollArea`. Tailwind v4 — no config file, use existing `@theme` tokens from `app/globals.css`. Async `params` if the route takes any. Use Server Actions for sending new messages."*

### For a Gemini call
> *"Add a function `async def ask_records(patient_id, question)` using the `google-genai` SDK with `vertexai=True, location='europe-west3'`. Embed the question with `text-embedding-004`. Query pgvector with `<=>` cosine distance, filtered by `patient_id` in SQL. Call `gemini-2.5-pro` with retrieved records as context and the system prompt from `app/ai/prompts/records-qa.system.md`. Return answer text + list of cited record IDs."*

## Drop-in context file for assistants

Claude Code reads `CLAUDE.md`. Gemini Code Assist reads `GEMINI.md` or similar. Both read any file you feed them. We'll keep the canonical stack context in [`04-tech-stack.md`](04-tech-stack.md) and reference it from `CLAUDE.md` at the repo root.

When starting a new session with an assistant, open these files in context:
- `docs/04-tech-stack.md` (the contract)
- `docs/09-ai-assist-playbook.md` (this file)
- Whichever doc covers the feature you're building

## When in doubt

Ask the assistant to show you the import statements and package versions it's assuming. If it names `google-generativeai`, `vertexai.generative_models`, Pydantic `class Config`, `session.query()`, or a `tailwind.config.js` — stop it. Repeat the golden-rule preamble. Try again.
