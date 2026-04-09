# Documentation Index

Single source of truth for the **Longevity MVP** — BCG Platinion AI Hackathon, Future Leader Summit Hamburg, 09–10.04.2026.

> **For AI assistants (Claude Code, Gemini Code Assist, Codex):** read `04-tech-stack.md` and `09-ai-assist-playbook.md` before generating code. Both contain version pins and known hallucination traps for this stack.

## How these docs are organized

Each file is scoped to one concern and kept short so it fits cleanly into an LLM context window. Read top-to-bottom for full context, or jump to the section you need.

| # | File | Purpose | Audience |
|---|---|---|---|
| 01 | [Vision & Strategy](01-vision.md) | Problem, goals, north-star metric, monetization, competitive positioning | Everyone, pitch |
| 02 | [Persona, Journey & User Stories](02-persona-and-journey.md) | Anna persona, longevity journey, 3+ user stories | Product, design, pitch |
| 03 | [System Architecture](03-architecture.md) | Component diagram, request flow, deployment topology | Engineering, pitch |
| 04 | [Tech Stack (LOCKED)](04-tech-stack.md) | Every pinned version, why each choice | Engineering, AI assistants |
| 05 | [Data Model & Adapter Layer](05-data-model.md) | Unified patient profile, pluggable data sources | Backend devs |
| 06 | [AI Layer](06-ai-layer.md) | Gemini models, RAG, prompts, safety framing | Backend/AI devs |
| 07 | [Feature Scope](07-features.md) | MVP features (must/nice/deferred), demo flow | Everyone |
| 08 | [Legal & Compliance](08-legal-compliance.md) | GDPR, EU AI Act, MDR stance | Pitch, backend |
| 09 | [AI-Assist Playbook](09-ai-assist-playbook.md) | Prompt patterns + traps for Claude/Gemini Code Assist | All devs |
| 10 | [Team & Workflow](10-team-and-workflow.md) | Pod structure, 24h timeline, branch strategy | Everyone |

## Provided materials

- [`provided/`](provided/) — Challenge deep-dive deck (PDF + PPTX) from BCG Platinion

## Datasets

Raw datasets live in `/data` (outside `/docs`):
- `ehr_records.csv` — 1,000 synthetic patients (diagnoses, medications, visits)
- `wearable_telemetry_1.csv` — 90-day wearable history per patient
- `lifestyle_survey.csv` — self-reported diet, exercise, stress
- `data_dictionary.xlsx` — field definitions

## Conventions

- **Don't duplicate**: each fact lives in exactly one doc. Cross-link with relative paths.
- **Update in place**: docs are living. Don't append "v2" sections — edit the original and let git carry history.
- **Flag uncertainty**: open questions go in a `## Open questions` section at the end of the relevant doc.
