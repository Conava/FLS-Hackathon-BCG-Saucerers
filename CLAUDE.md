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
