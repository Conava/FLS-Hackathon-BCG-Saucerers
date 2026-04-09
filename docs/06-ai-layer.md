# 06 — AI Layer

Three distinct AI capabilities, each backed by a specific Gemini model and a specific prompt strategy.

For SDK version + pricing see [04-tech-stack.md](04-tech-stack.md). For system placement see [03-architecture.md](03-architecture.md).

## Capability matrix

| Capability | Model | Why this model | Input shape | Output shape |
|---|---|---|---|---|
| **AI Health Coach** (chat) | **Gemini 2.5 Flash** | Fast, cheap, 1M context fits full patient profile | System prompt + patient profile summary + chat history + user message | Streaming text + optional structured actions |
| **NL Record Q&A** (RAG) | **Gemini 2.5 Pro** | Needs reasoning quality for medical record interpretation | System prompt + top-k retrieved records + user question | Text answer + citation IDs |
| **Smart Notifications** | **Gemini 2.5 Flash** | Volume + low latency | Event trigger + patient context + user preferences | One notification (title, body, CTA) |
| **Analytics Narration** | **Gemini 2.5 Flash** | Turn score changes into plain-language story | Score delta + contributing factors | Short paragraph |
| **Future-Self Simulator** | **Gemini 2.5 Flash** | Narrative generation | Current state + projected state | "Here's you at 70 on current trajectory vs improved" text |
| **Embeddings** | **`text-embedding-004`** | 768d, integrates with pgvector | Text chunks | `list[float]` (768) |

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
├── coach.user-preamble.md
├── records-qa.system.md
├── notifications.system.md
├── analytics-narration.system.md
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
- ~100 RAG queries × 4k tokens avg on Pro = $4.00
- Embeddings for full dataset: 1,000 patients × ~20 records × 200 tokens = $0.50

Total: **<$10 for the entire hackathon.** GCP credits cover it.

## Open questions

- Do we stream coach responses (better UX) or batch (simpler)? Leaning stream — it's a killer demo moment.
- Do we fine-tune a small model later, or stay prompt-engineered? Stay prompt-engineered for MVP. Fine-tuning is a v2 slide.
- Reranking in the RAG pipeline: needed for MVP or skip? Skip for MVP — top-8 cosine is enough on a 1,000-patient corpus.
