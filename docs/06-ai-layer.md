# 06 — AI Layer

Three distinct AI capabilities, each backed by a specific Gemini model and a specific prompt strategy.

For SDK version + pricing see [04-tech-stack.md](04-tech-stack.md). For system placement see [03-architecture.md](03-architecture.md).

## Capability matrix

| Capability | Model | Why this model | Input shape | Output shape |
|---|---|---|---|---|
| **AI Health Coach** (chat, general) | **Gemini 2.5 Flash** | Fast, cheap, 1M context fits full patient profile | System prompt + patient profile summary + survey RAG + chat history + user message | Streaming text + optional structured `ProtocolAction` suggestions |
| **Records Q&A** (EHR-scoped RAG) | **Gemini 2.5 Pro** | Reasoning quality for medical record interpretation; **strictly** scoped to provider records | System prompt + top-k retrieved `EHRRecord`s + user question | Text answer + citation IDs |
| **Protocol Generator** | **Gemini 2.5 Pro** | Structured reasoning over goals + biomarkers + survey + constraints; one call per week per patient | System prompt + patient profile + active biomarkers + `LifestyleProfile` + prior-week adherence | Structured JSON: 3–7 `ProtocolAction` objects + rationale |
| **Meal Vision** | **Gemini 2.5 Flash (vision)** | Low latency, multimodal, good enough for food classification + macro estimation | Photo + dietary restrictions from `LifestyleProfile` | Structured JSON: classification, macros, **one-line longevity swap** |
| **Outlook Narrator** | **Gemini 2.5 Flash** | Turn the streak-driven Outlook curve into one sentence on Today | `VitalityOutlook` row + top 2 driver categories | One sentence: *"Hold your streak and your Outlook reaches 74 by October — mostly from sleep consistency."* |
| **Future-Self Simulator** | **Gemini 2.5 Flash** | Long-horizon narrative generation | Current state + slider-adjusted state | "Here's you at 70 on current trajectory vs improved" text |
| **Smart Notifications** | **Gemini 2.5 Flash** | Volume + low latency | Event trigger + patient context + user preferences | One notification (title, body, CTA) |
| **Analytics Narration** | **Gemini 2.5 Flash** | Turn score changes into plain-language story | Score delta + contributing factors | Short paragraph |
| **Embeddings** | **`text-embedding-004`** | 768d, integrates with pgvector | Text chunks (EHR records + free-text survey answers) | `list[float]` (768) |

### Coach vs. Records — deliberate separation

The product keeps these as two distinct AI surfaces, not one. Same model family, different contracts:

| | **Coach** | **Records Q&A** |
|---|---|---|
| Scope | General longevity, lifestyle, nutrition | **Only** the provider's EHR + labs + imaging |
| Context | Full patient profile (EHR + wearable + survey + meal logs + protocol) | Top-k retrieved `EHRRecord`s for this patient |
| Can invent advice? | Yes — general guidance, cites sources where relevant | **Never** — if it's not in the retrieved records, answer is "I don't have that information" |
| Can write to protocol? | Yes — suggests `ProtocolAction`s that land on Today | No — read-only |
| Tone | Conversational, motivational, nutrition-savvy | Clinical, precise, citation-heavy |

Prompts: `coach.system.md` (Flash, loose) vs. `records-qa.system.md` (Pro, strict).

## SDK usage pattern (locked)

```python
from google import genai

# Routes through Vertex AI → billed to GCP credits
client = genai.Client(
    vertexai=True,
    project="our-gcp-project",
    location="europe-west3",
)

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=[...],
    config=genai.types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        temperature=0.3,
        safety_settings=[...],
    ),
)
```

**Do NOT use:** `google-generativeai` (old), `vertexai.generative_models` (deprecated). See [09-ai-assist-playbook.md](09-ai-assist-playbook.md).

## Prompt architecture

All prompts live in `app/ai/prompts/` as versioned `.md` files (not string literals in Python). Reasons:
- Non-engineers (strategy pod) can edit prompts without touching code
- Diffs are reviewable in git
- LLM assistants can read/write them without parsing Python AST
- We can A/B variants by filename

```
app/ai/prompts/
├── coach.system.md
├── records-qa.system.md
├── protocol-generator.system.md
├── meal-vision.system.md
├── outlook-narrator.system.md
├── notifications.system.md
└── future-self.system.md
```

Loaded via a simple helper:
```python
def load_prompt(name: str) -> str:
    return (Path(__file__).parent / "prompts" / f"{name}.md").read_text()
```

## RAG pipeline (the killer demo feature)

The "ask your records anything" flow. Architecturally small, demo-wise huge.

```
User question
    │
    ▼
Embed via text-embedding-004  (768d)
    │
    ▼
SQL: SELECT ... FROM ehr_records
     WHERE patient_id = :pid                      ← hard isolation
     ORDER BY embedding <=> :query_vec            ← cosine distance
     LIMIT 8;
    │
    ▼
Rerank + prune to fit context (optional, skip for MVP)
    │
    ▼
Gemini 2.5 Pro call
   system:  records-qa.system.md (safety framing + citation requirement)
   content: retrieved records (with IDs) + user question
    │
    ▼
Response with [ref:record_id] citations
    │
    ▼
Client renders answer + clickable citation chips
```

### Non-negotiable RAG rules

1. **Patient isolation at SQL level.** Never rely on post-hoc filtering. `WHERE patient_id = :pid` in the retrieval query itself.
2. **Always cite.** System prompt requires every factual claim to cite a record ID. If the model can't cite, it must say "I don't have that information."
3. **Never hallucinate values.** If ApoB isn't in the retrieved records, don't invent a number. System prompt explicit on this.
4. **Safety framing.** Every response includes an implicit disclaimer: this is not medical advice, a clinician reviews anything actionable.
5. **Log request IDs, not content.** LLM observability without PHI leakage.

## Protocol Generator — structured output contract

One Gemini 2.5 Pro call per week per patient (also on survey retake, or on explicit user "re-plan"). Structured JSON out, validated against a Pydantic schema before writing to `Protocol` + `ProtocolAction` rows.

```python
class GeneratedAction(BaseModel):
    category: Literal["movement", "sleep", "nutrition", "mind", "supplement"]
    title: str
    target: str
    rationale: str                           # one line, shown under the action on Today
    dimension: Literal["biological_age", "sleep_recovery", "cardio_fitness", "lifestyle_behavioral"]

class GeneratedProtocol(BaseModel):
    rationale: str                           # one paragraph shown at the top of Today's protocol
    actions: list[GeneratedAction]           # 3–7 items
```

**Input context:**
- `LifestyleProfile` (typed survey) — including `time_budget_minutes_per_day`, `out_of_pocket_budget_eur_per_month`, `dietary_restrictions`, `injuries_or_limitations` (these are hard constraints)
- Latest `VitalitySnapshot` sub-scores + flags
- Recent 7-day wearable trend summary
- Prior-week adherence from `DailyLog` (so Coach can tune difficulty)

**Hard rules in `protocol-generator.system.md`:**
1. Respect `time_budget_minutes_per_day` — total protocol time must fit.
2. Never recommend supplements or diagnostics exceeding `out_of_pocket_budget_eur_per_month`.
3. Never contradict `dietary_restrictions` or `known_allergies`.
4. Every action must carry a one-line rationale the user can act on.
5. Each action is tagged with exactly one of the four longevity dimensions.
6. Generate between 3 and 7 actions (inclusive).
7. Actions for users with `injuries_or_limitations` must not aggravate them.
8. Never use ICD-10 codes, disease names, or diagnostic language in action titles, targets, or rationales — use wellness framing (e.g. "support joint mobility" not "treat arthritis").
9. The top-level `rationale` field must include AI-disclosure phrasing (e.g. "This AI-generated protocol…").

## Meal Vision — structured output contract

```python
class MealAnalysis(BaseModel):
    classification: str                      # "grilled salmon, white rice, broccoli"
    macros: dict                             # {kcal, protein_g, carbs_g, fat_g, fiber_g}
    longevity_swap: str                      # one-line swap or "" if already optimized
    swap_rationale: str                      # one line explaining the longevity benefit
```

Called on meal photo upload. Result writes a `MealLog` row and updates Today's protein/fiber rings in the UI. Cheap, high-wow, pre-cache a canned example for demo-day as fallback (Gemini vision latency is the one thing we can't guarantee on stage — see [07-features.md](07-features.md) contingencies).

## Safety & framing (legal-driven)

Per [08-legal-compliance.md](08-legal-compliance.md), we stay out of the MDR Class IIa medical-device bucket by:

| Do | Don't |
|---|---|
| "Your habits suggest your sleep could improve" | "You have insomnia" |
| "Your wearable data shows a pattern worth discussing with your doctor" | "You may have arrhythmia" |
| "This is not medical advice" disclaimers in prompts | Diagnostic verbs: diagnose, treat, cure, prevent-disease |
| Human-in-the-loop for clinical actions | AI auto-books medical interventions without user confirmation |
| Cite retrieved records, never invent | Fabricate biomarker values |

Every system prompt encodes these rules. Review all prompts before demo.

## Observability (lightweight)

- Log `(request_id, model, prompt_name, token_in, token_out, latency_ms)` — no PHI
- Store last 50 coach turns per patient in Postgres (for conversation continuity, not analytics)
- Demo-day dashboard: Cloud Logging filter by `model=` for live call visibility if a judge asks

## Cost ceiling for demo day

Back-of-envelope for 24h hackathon + 10 demo runs:
- ~200 coach turns × 2k tokens avg on Flash = $0.60
- ~100 Records Q&A queries × 4k tokens avg on Pro = $4.00
- ~20 Protocol Generator runs × 6k tokens on Pro = $2.00
- ~50 Meal Vision calls × 1.5k tokens on Flash (vision) = $0.80
- ~100 Outlook Narrator calls × 0.5k tokens on Flash = $0.10
- Embeddings: 1,000 patients × ~20 records × 200 tokens + ~30 survey responses × 150 tokens = $0.60

Total: **<$15 for the entire hackathon.** GCP credits cover it.

## Implementation notes (slice 2)

- **Coach streaming:** `POST /v1/patients/{patient_id}/coach/chat` returns `text/event-stream` via `sse_starlette.EventSourceResponse`. Events: `token`, optional `protocol_suggestion`, `done` (with `ai_meta`). The `FakeLLMProvider` yields a small fixed sequence for tests.
- **LLM abstraction:** `app/ai/llm.py` exposes an `LLMProvider` Protocol with four methods: `generate`, `generate_stream`, `embed`, `generate_vision`. Set `LLM_PROVIDER=fake` (default) for dev/CI; `LLM_PROVIDER=gemini` for production.
- **Prompt files:** `app/ai/prompts/` contains all seven `.system.md` files. Loaded by `app/ai/prompt_loader.py` with in-process caching; raises `FileNotFoundError` on a miss.
- **Reranking:** skipped for MVP — top-8 cosine is sufficient on the 1,000-patient corpus.
