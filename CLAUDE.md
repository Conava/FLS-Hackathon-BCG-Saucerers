# CLAUDE.md

This file is the single source of non-obvious project context — things that cannot be figured out from the code, tests, or git history alone. Do not add anything here that is already discoverable or obvious.

## Workflow Orchestration

### Pipeline First
- Use `/devline` for any non-trivial task (3+ steps or architectural decisions). It handles brainstorming, planning, parallel implementation, review, and documentation.
- Use `/devline:implement` only for small, well-scoped tasks where the plan is obvious.
- If something goes sideways during implementation, stop and re-plan — do not patch forward.

### Subagent Strategy
- Use subagents liberally to keep the main context window clean.
- Offload research, exploration, and parallel analysis to subagents.
- For complex problems, throw more compute at it via subagents — one task per subagent for focused execution.

## Core Principles

- **Simplicity First**: Make every change as simple as possible.
- **No Laziness**: Find root causes. No temporary fixes. Senior developer standards.
- **Demand Elegance**: For non-trivial changes, pause and ask "is there a more elegant way?" If a fix feels hacky, implement the elegant solution. Skip this for simple, obvious fixes — don't over-engineer.
- **Minimize Output Noise**: When running commands that may produce large output (test suites, logs, builds), proactively use `| grep`, `| head`, or flags like `--quiet`/`--failed-only` to filter results. Only run unfiltered if filtered output is insufficient.

## Learning & Recovery

This project uses a self-correcting pipeline. Agents (implementer, reviewer, deep-review) continuously challenge themselves: "Is this a one-off issue or a broader pattern?" When they identify a non-obvious codebase pattern, they report it as a lesson and the orchestrator appends it to the Lessons and Memory section below.

**For the pipeline (automatic):** Agents extract lessons during normal work. No approval needed — the agent already analyzed the issue. Lessons are shown in the pipeline completion summary.

**For direct conversations (manual):** When the user corrects you or you discover a non-obvious pattern outside the pipeline:
1. Identify the root cause — not just the symptom.
2. Assess scope — one-off or pattern?
3. If it's a pattern, formulate as: pattern (what triggers it), reason (why it happens), solution (how to prevent it).
4. Append it to the Lessons and Memory section below.

**Always:** Review existing lessons before starting work. If a lesson covers the situation, follow it. Update stale lessons rather than adding duplicates.

## Project Context

This is the **BCG Platinion AI Hackathon** project (Future Leader Summit Hamburg, 09–10.04.2026): a 24-hour build of an **AI-driven longevity MVP** for a European healthcare group. 6-person team.

**Before writing code, read:**
- [`docs/README.md`](docs/README.md) — documentation index
- [`docs/04-tech-stack.md`](docs/04-tech-stack.md) — **LOCKED** versions (Next.js 15, FastAPI, SQLModel, Pydantic v2, SQLAlchemy 2.0 async, Cloud SQL Postgres 16 + pgvector, `google-genai` SDK with Gemini 2.5 Flash/Pro, Tailwind v4, Cloud Run europe-west3)
- [`docs/09-ai-assist-playbook.md`](docs/09-ai-assist-playbook.md) — **REQUIRED** — known AI-assistant hallucination traps for this stack (wrong Gemini SDK, Pydantic v1 syntax, SQLAlchemy 1.x, Tailwind v3 config, Next.js 14 sync params, etc.)

**For any code-writing prompt, include this preamble:**
> *Stack: FastAPI + SQLModel + SQLAlchemy 2.0 async + Pydantic v2 + `google-genai` SDK (NOT google-generativeai, NOT vertexai.generative_models) + Next.js 15 App Router + Tailwind v4 (no tailwind.config.js). See docs/04-tech-stack.md.*

**Key invariants** (non-negotiable — see docs/08-legal-compliance.md):
- Every SQL query filters by `patient_id` at the SQL level (hard isolation for GDPR + RAG safety)
- No PHI in logs — only request IDs, model names, token counts
- EU-region only (`europe-west3`) — Cloud Run, Cloud SQL, Vertex AI
- Wellness framing in all user-facing copy — no diagnostic verbs (diagnose/treat/cure/prevent-disease) to stay out of MDR Class IIa
- Every AI screen discloses "You're talking to an AI"

## Lessons and Memory

<!-- Lessons are added here automatically via the Learning & Recovery process above. -->
<!-- Format: **Pattern**: ... | **Reason**: ... | **Solution**: ... -->

**Pattern**: `datetime` fields in SQLModel map to `TIMESTAMP WITHOUT TIME ZONE`; asyncpg rejects timezone-aware values at insert time. **Reason**: SQLModel's default column type carries no timezone. asyncpg raises `"can't subtract offset-naive and offset-aware datetimes"` when a `tzinfo`-bearing value is bound. **Solution**: always construct datetimes as naive UTC — `datetime.now(UTC).replace(tzinfo=None)`. Never use `datetime.utcnow()` (deprecated in Python 3.12+).

**Pattern**: Combining `Field(index=True)` on a column with a named `Index` on the same column in `__table_args__` causes a duplicate-index DDL crash at `create_all`. **Reason**: SQLModel/SQLAlchemy emits two `CREATE INDEX` statements for the same column. **Solution**: pick one — prefer `__table_args__` when you need a named index for the pitch; drop `Field(index=True)` on the same column.

**Pattern**: `uv run` does not inherit shell environment variables such as `DOCKER_HOST`. **Reason**: `uv` launches a subprocess that may not carry the calling shell's exports. **Solution**: set rootless Docker socket paths at conftest module-load time (e.g. `os.environ.setdefault("DOCKER_HOST", "unix:///run/user/...")`) before Testcontainers initialises.

**Pattern**: asyncpg + session-scoped pytest-asyncio fixtures deadlock or raise loop-scope errors without explicit scope configuration. **Reason**: pytest-asyncio defaults to function scope for the event loop, conflicting with session-scoped async fixtures that share a DB connection. **Solution**: set both `asyncio_default_fixture_loop_scope = "session"` and `asyncio_default_test_loop_scope = "session"` in `[tool.pytest.ini_options]` in `pyproject.toml`.

**Pattern**: pytest `@pytest.mark.X` marker declarations do not skip tests by default — they only categorise them. **Reason**: markers are metadata; exclusion requires explicit `addopts`. **Solution**: add `addopts = "-m 'not X'"` to `[tool.pytest.ini_options]` for any marker (e.g. `compose`) that should be deselected in the standard `uv run pytest` run.

**Pattern**: `python-json-logger` v3+ moved the formatter class to the `pythonjsonlogger.json` submodule; importing from `pythonjsonlogger.jsonlogger` raises an `ImportError`. **Reason**: the submodule was renamed in the v3 release. **Solution**: import `from pythonjsonlogger.json import JsonFormatter` (not `.jsonlogger`). Pin to `>=3.0` and update any legacy import paths.

**Pattern**: `SQLModel.column == value` comparisons in `.where()` clauses type-check as `bool` under mypy strict mode, not as a SQLAlchemy `ColumnElement`. **Reason**: SQLModel's `Field` descriptors return `bool` from `__eq__` in mypy's view. **Solution**: use `getattr(Model, "column_name")` (typed `Any`) to build the comparison — e.g. `getattr(Patient, "patient_id") == patient_id`. This is the consistent pattern used across all repositories in this codebase.

**Pattern**: Tailwind v4 does not support `shadows` inside the `@theme` block — only CSS custom properties are valid there. **Reason**: Tailwind v4's `@theme` directive only processes color, spacing, font, and similar design tokens; shadow utilities need a different mechanism. **Solution**: declare shadow values as plain CSS custom properties in `:root { --shadow-sm: …; }` and expose them as utilities via `@layer utilities { .shadow-app-sm { box-shadow: var(--shadow-sm); } }`. Never put shadows in `@theme`.

**Pattern**: The Next.js 15 Route Handler proxy for SSE (`text/event-stream`) must use `export const runtime = "nodejs"` (not the default edge runtime). **Reason**: the edge runtime's `fetch` implementation does not support streaming response bodies for Server-Sent Events in all environments. **Solution**: add `export const runtime = "nodejs"` to the proxy route file (`src/app/api/proxy/[...path]/route.ts`) and stream the `response.body` directly into the `NextResponse` body without buffering.

**Pattern**: The PWA service worker must explicitly bypass SSE endpoints and non-GET API requests; a naive cache-first or network-first strategy will break streaming. **Reason**: a service worker intercepts all fetches, including EventSource connections; caching or re-fetching a stream yields an already-consumed `ReadableStream`. **Solution**: in the `fetch` handler, check `event.request.url.includes('/coach/chat')` (or the SSE path) and `event.request.method !== 'GET'` and call `event.respondWith(fetch(event.request))` (pass-through) for those cases before any cache logic.

**Pattern**: `lucide-react` icons do not match the custom mockup SVG paths used in this project's design system. **Reason**: Lucide uses its own standardised icon set. **Solution**: the project maintains its own icon set in `src/components/design/` with stroke icons matching the mockup exactly. Use `lucide-react` only for incidental utility icons (loading spinners, generic arrows) where pixel-perfect mockup fidelity is not required.
