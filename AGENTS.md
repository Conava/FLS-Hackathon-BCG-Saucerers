# AGENTS.md

This file is the Codex baseline for every thread created inside this repository. Because it lives at the repo root, it applies across all subfolders and should be treated as the default operating prompt for future Codex work here.

Use this file together with [CLAUDE.md](C:\Users\mik-m\Downloads\ai hack real\CLAUDE.md). If guidance overlaps, follow the stricter rule.

## Read First

Before writing code, review these files:

- [CLAUDE.md](C:\Users\mik-m\Downloads\ai hack real\CLAUDE.md)
- [README.md](C:\Users\mik-m\Downloads\ai hack real\README.md)
- [docs/04-tech-stack.md](C:\Users\mik-m\Downloads\ai hack real\docs\04-tech-stack.md)
- [docs/07-features.md](C:\Users\mik-m\Downloads\ai hack real\docs\07-features.md)
- [docs/09-ai-assist-playbook.md](C:\Users\mik-m\Downloads\ai hack real\docs\09-ai-assist-playbook.md)
- [backend/README.md](C:\Users\mik-m\Downloads\ai hack real\backend\README.md)
- [mockup/index.html](C:\Users\mik-m\Downloads\ai hack real\mockup\index.html)

## Project Mission

You are building a health-focused app for BCG Platinion. The product combines data from external systems and tracking apps, calculates health-related metrics, and turns those metrics into clear insights and guidance.

Treat the backend and project docs as the source of truth. Do not invent system behavior when the repository already defines it.

## Repo Reality

- The backend is already implemented for slice 1 in [backend/](C:\Users\mik-m\Downloads\ai hack real\backend).
- The frontend application is not yet built as a production app.
- The current UI contract lives in [mockup/index.html](C:\Users\mik-m\Downloads\ai hack real\mockup\index.html).
- The locked frontend target is Next.js 15 + React 19 + Tailwind v4 + shadcn/ui + TypeScript strict.
- The current live backend surface is read-only slice 1:
  - `GET /healthz`
  - `GET /patients/{patient_id}/profile`
  - `GET /patients/{patient_id}/vitality`
  - `GET /patients/{patient_id}/records`
  - `GET /patients/{patient_id}/wearable`
  - `GET /patients/{patient_id}/insights`
  - `GET /patients/{patient_id}/appointments`
  - `GET /patients/{patient_id}/gdpr/export`
  - `DELETE /patients/{patient_id}/gdpr`
- AI coach, records Q&A, meal vision, protocol generation, and other slice 2 frontend-facing flows are not implemented in the backend yet unless the code added later proves otherwise.

## Branch And Git Safety

Before continuing with any task:

- Check the current branch and working tree state.
- Confirm that you are working with the latest available git changes relevant to the task.
- Review the branch diff before editing so you understand what already exists.
- Do not overwrite, revert, or casually refactor changes already present on the current branch unless the user explicitly asks or those changes come directly from syncing with `main`.
- If you cannot safely verify branch ownership or latest upstream state, stop and ask for clarification or permission to fetch.

## Frontend Working Mode

Most frontend tasks in this repo should be handled as isolated fragments.

- Focus only on the fragment the user asked to evaluate or improve.
- Use other pages and fragments only as references for consistency, navigation, spacing, tone, and interaction design.
- Keep the experience continuous and smooth across Today, Coach, Records, Insights, Care, and Me.
- Preserve the mobile-first PWA feel established by the mockup.
- Do not broaden scope into unrelated screens unless that is necessary for consistency or explicitly requested.

## Backend-To-Frontend Rule

Every time you implement frontend work:

- Check the backend routers, schemas, repositories, and services first when the UI depends on real data or behavior.
- Wire the frontend to real endpoints, payloads, and states whenever they already exist.
- If the requested UX depends on backend capability that does not exist yet, do not invent an API contract silently.
- In that case, clearly surface the gap and ask whether to stub the UI, add a placeholder state, or extend the backend.

## Product And Compliance Guardrails

- Keep user-facing language wellness-focused rather than diagnostic or treatment-oriented.
- Any AI-facing screen or conversational surface must disclose that the user is interacting with AI.
- Respect the four longevity dimensions and the app structure defined in [docs/07-features.md](C:\Users\mik-m\Downloads\ai hack real\docs\07-features.md).
- Use the repo's actual product language: Today, Coach, Records, Insights, Care, and Me.

## Technical Guardrails

- Follow the locked stack in [docs/04-tech-stack.md](C:\Users\mik-m\Downloads\ai hack real\docs\04-tech-stack.md).
- Avoid outdated patterns called out in [docs/09-ai-assist-playbook.md](C:\Users\mik-m\Downloads\ai hack real\docs\09-ai-assist-playbook.md).
- If you build or scaffold frontend code, default to Next.js 15 App Router patterns and Tailwind v4 conventions.
- Do not introduce deprecated assumptions such as Next.js 14 sync route params or a Tailwind v3 `tailwind.config.js`.

## Self-Questioning Checklist

Before making a change, answer these questions:

1. What exact frontend fragment is in scope?
2. Which existing screen or mockup section should this align with?
3. What backend route, schema, or service powers this interaction today?
4. What is real in the repo, and what is still only planned?
5. What would break continuity if this fragment changed in isolation?
6. Am I preserving existing branch work?
7. Is there any risky assumption that should be confirmed with the user first?

## Definition Of Done

A frontend task is not done until:

- The requested fragment is improved and aligned with surrounding UI patterns.
- Relevant backend integration has been checked.
- Missing backend dependencies are called out instead of guessed.
- The result has been self-reviewed against this file and [CLAUDE.md](C:\Users\mik-m\Downloads\ai hack real\CLAUDE.md).
- After completing a meaningful implementation, pause and ask the user to review before moving on to a separate fragment.
