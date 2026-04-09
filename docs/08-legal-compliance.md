# 08 — Legal & Compliance

A European longevity app handling health data is a regulatory minefield. Most hackathon teams will ignore this. **One slide mentioning it is a massive differentiator to BCG Platinion judges** — because they live in this world and advise real clients on it.

This doc is both an engineering checklist (what to bake into the MVP) and a pitch talking-points source.

## The four regimes we have to live with

1. **GDPR** (especially Art. 9 — special-category health data)
2. **EU AI Act** (in force 2024, obligations phased through 2026–27)
3. **Medical Device Regulation (MDR 2017/745)**
4. **ePrivacy + national rules** across 9 countries

## GDPR — bake into MVP

| Requirement | Our MVP stance |
|---|---|
| **Art. 9 special-category data** | Explicit, granular, revocable consent. Separate consents per purpose (care, research, marketing). |
| **DPIA** (Data Protection Impact Assessment) | Checklist slide in pitch appendix. Real DPIA before production. |
| **DPO** | Clinic group already has one. Product team reports into them. |
| **Lawful basis** | Art. 9(2)(h) — provision of healthcare — for clinical features; explicit consent for optional/wellness features. |
| **Data residency** | EU-only. Cloud SQL + Cloud Run in `europe-west3` (Frankfurt). No US sub-processors for PHI without SCCs + Transfer Impact Assessment. |
| **Right to access / erasure** | API endpoints `GET /patients/me/export` and `DELETE /patients/me` — MVP stub + pitch slide. Erasure must cascade through `Protocol`, `ProtocolAction`, `DailyLog`, `MealLog`, `SurveyResponse`, `VitalitySnapshot`, `VitalityOutlook` — not just `Patient` + `EHRRecord`. |
| **Patient isolation** | SQL-level `WHERE patient_id = :pid` on every query. See [03-architecture.md](03-architecture.md). |
| **New PHI categories in v1 scope** | Beyond EHR: **meal photos** (uploaded images — Cloud Storage, EU bucket, patient-scoped ACLs, deletable), **detailed survey answers** (`SurveyResponse` — dietary restrictions, alcohol intake, budget, injuries — all Art. 9 territory), **self-tracked logs** (`DailyLog` — mood, sleep, workouts), **protocol adherence** (streaks + completion). All patient-scoped, EU-hosted, consent-gated. |
| **Meal photo retention** | Stored only as long as the `MealLog` row references them. Erasure request deletes the Cloud Storage object. Consider an opt-out: "analyze but don't store the photo" — v2. |

## EU AI Act — risk classification is everything

The AI Act classifies AI systems by risk tier. Where we sit decides whether we ship in 24 hours or 24 months.

| Tier | What triggers it | Our stance |
|---|---|---|
| **Minimal** | Simple chatbot, no clinical content | Too weak — we want personalization |
| **Limited risk** | AI that interacts with humans, generates content | **Our target.** Transparency obligations only: clearly disclose AI, no deception. |
| **High risk** | Triage, diagnosis, treatment recommendation, safety components of medical devices | **Avoid at MVP.** Requires conformity assessment, risk management, human oversight, full logging, post-market monitoring. |
| **Unacceptable** | Social scoring, manipulation | N/A |

### How we stay "limited-risk" (not high-risk)

- ✅ **Clear AI disclosure** in every screen that uses the coach ("You're talking to an AI assistant")
- ✅ **Human-in-the-loop for clinical actions** — AI flags, clinician confirms before anything prescriptive
- ✅ **Full interaction logging** — request IDs, model name, token counts (no PHI)
- ✅ **No diagnostic or triage language** — see MDR below
- ❌ **Don't** let the AI auto-book medical interventions
- ❌ **Don't** let it rank patients by clinical risk for clinician dashboards (that would cross into triage)

## MDR — the Class IIa trap

This is the subtle one. Under MDR + MDCG 2019-11, any software with a **medical purpose** (diagnose, prevent, monitor, predict, treat disease) can become a **Class IIa medical device** under Rule 11. Class IIa means:
- Notified body conformity assessment
- CE marking
- 12–18 months of process
- Clinical evidence package
- **Completely out of reach for a 24h hackathon**

### Our escape hatch: framing

We frame the product as **wellness / lifestyle**, not medical. That's a legal distinction enforced through **language and scope**, not technology.

| Wellness framing (OK) | Medical framing (triggers MDR) |
|---|---|
| "Vitality Score" | "Disease risk score" |
| "Vitality Outlook" / "your projected score if you keep this streak" | "Disease progression forecast" |
| "Future-self simulator — what your habits project at 70" | "Mortality prediction" / "life expectancy calculator" |
| "Daily protocol" / "today's actions" | "Treatment plan" / "prescription" |
| "Longevity swap" / "a better choice for your goals" | "Dietary therapy for condition X" |
| "Your habits suggest your sleep could improve" | "You have insomnia" |
| "Cardiovascular fitness" | "Risk of cardiovascular disease" |
| "A pattern worth discussing with your doctor" | "Evidence of arrhythmia" |
| "General wellness and prevention" | "Diagnosis, treatment, or prevention of disease" |
| "Supports healthy habits" | "Treats / cures / prevents X" |
| Generic ranges | ICD-10 codes |

**Engineering implication:** every prompt in [`06-ai-layer.md`](06-ai-layer.md) encodes these rules. Copy review by the strategy pod before demo.

### DiGA (Germany) — v2 opportunity, not MVP

DiGA lets apps be reimbursed by German statutory insurance up to ~€200/user/year. Sounds amazing. **But:**
- Requires Class I or IIa MDR certification first
- Needs clinical evidence
- 12-month BfArM listing process

**Verdict:** defer to v2. But design the data model so a future DiGA spin-out is viable. Pitch line: *"Wellness today, reimbursable medical device tomorrow — the architecture supports both paths."*

## Liability

- **AI recommendations:** clinician co-sign for anything clinical. T&Cs with clear scope. Product liability insurance (the clinic already has this).
- **AI Liability Directive** (pending): will tighten burden of proof on AI providers. Design for traceability now (full interaction logging).
- **"Not medical advice" disclaimer** in every coach screen and at the bottom of every record-QA response.

## ePrivacy + per-country rules

Nine countries means nine slightly different consent + cookie + telemedicine regimes. For MVP: use the strictest common denominator (German rules are usually it).

- EU cookie consent banner via a standard library
- No third-party trackers on health-data screens
- Telemedicine features gated per country (deferred to v2 — mock a single country for demo)

## Engineering checklist — bake into MVP now

- [ ] Every SQL query filters by `patient_id` (hard isolation) — including new tables: `Protocol`, `ProtocolAction`, `DailyLog`, `MealLog`, `SurveyResponse`, `VitalityOutlook`
- [ ] Every AI prompt contains "not medical advice" framing + wellness-language rules — including `protocol-generator.system.md`, `meal-vision.system.md`, `outlook-narrator.system.md`
- [ ] Every AI screen has a visible "You're talking to an AI" disclosure — Coach, Records Q&A, Meal Vision result, Protocol rationale, Outlook narration, Future-self simulator
- [ ] Log only request IDs + model name + tokens, never PHI content (never log meal photo bytes, survey free-text, or protocol contents)
- [ ] EU-region only — verify Cloud Run, Cloud SQL, Vertex AI, **and Cloud Storage (meal photo bucket)** all in `europe-west3`
- [ ] `GET /patients/me/export` and `DELETE /patients/me` endpoints — cascade through all new tables and delete Cloud Storage meal photo objects
- [ ] No ICD-10 codes, no disease names, no diagnostic verbs in user-facing copy **or in protocol action titles/rationales**
- [ ] Consent checkbox on onboarding (single checkbox OK for MVP, note real granularity is v2)
- [ ] Survey retake flow re-confirms consent for new categories (photo, detailed lifestyle)

## Pitch slide content

**Title:** "Wellness today. Medical device tomorrow. EU-native throughout."

**Bullets:**
- GDPR Art. 9 compliant by design — EU-hosted, patient-scoped queries, human-in-the-loop
- EU AI Act: limited-risk tier (transparency obligations only)
- MDR: wellness framing keeps us out of Class IIa for v1 launch
- v2 track: DiGA certification for German statutory reimbursement (~€200/user/year)
- Liability: clinician oversight on all clinical actions; full interaction logging for AI Liability Directive

One slide. Judges will smile. Most teams will skip this entirely.

## Open questions

- Do we need country-specific copy variants for the pitch, or is the "EU-first" framing enough?
- Does the clinic group already have a DPO we can name on the slide for credibility?
