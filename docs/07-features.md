# 07 — Feature Scope & Demo Flow

What we build, what we fake, what we defer, and the exact 3-minute story we tell on stage.

## Must-have (from the brief + our extension)

From the BCG brief:
- [x] **AI health coach** with personal, evidence-grounded recommendations
- [x] **Risk and opportunity flagging** with actionable interventions
- [x] **In-app commercial touchpoints** — diagnostics, packages, supplements surfaced contextually

From our product thinking:
- [x] **Unified patient profile** — EHR + wearable + lifestyle in one place
- [x] **Vitality Score** — single composite daily-return hook
- [x] **NL record Q&A** — "ask your records anything" via RAG (killer feature)
- [x] **Appointment management** — view + book + manage, in-network and external
- [x] **Custom notifications** — user-defined categories + AI-curated timing
- [x] **Multi-OS** — PWA works on web + iOS + Android + desktop; Capacitor wrap demonstrates native story

## Nice-to-have (build if time permits after core flow works)

- [ ] **Future-self simulator** — "here's you at 70 on current trajectory vs. improved" (biggest wow moment)
- [ ] **Supplement/diagnostic package storefront** — fully designed, one-tap purchase mock
- [ ] **Streaks + habit loop** — 7-day consistency badge
- [ ] **External doctor booking** — mocked Doctolib-style integration
- [ ] **Clinician handoff screen** — "a doctor is reviewing your result"

## Deferred (mentioned in pitch, not built)

- Real Doctolib/Jameda OAuth integration (mocked)
- Actual Apple Health / Fitbit API wiring (stubbed via adapter layer)
- Native iOS + Android builds (Capacitor wrap is a 1h showcase, not a shipped binary)
- Push notification infrastructure (in-app banners in demo)
- Auth / multi-tenant (demo uses a pre-loaded patient)
- DiGA certification (v2 track)
- Consent management UI beyond a single checkbox

## The 3-minute demo script

This is what we rehearse until it's flawless. Every screen earns its spot by selling one pillar of the pitch.

### Setup (pre-demo, not on stage)
Browser tabbed to the PWA. Anna's account pre-loaded with a realistic scenario: 42yo, recent lab showing elevated ApoB, 5 nights of poor sleep, Fitbit connected.

### 1. Onboarding story (0:00 – 0:20)
*"Meet Anna. 42, product manager in Hamburg. Her dad had a heart attack last year. She's a patient of our clinic network. Yesterday we emailed her: 'See your Vitality Score.'"*

→ Show: one-click login, 3-question lifestyle form, **instant score reveal**.

**Selling:** zero-friction activation. 10M warm leads → no CAC.

### 2. Dashboard (0:20 – 0:40)
*"This is Anna's morning. One number. One action."*

→ Show: Vitality Score 68 (down from 74), trend chart, today's nudge: *"You slept 5h 40m. Skip HIIT today — 25-min walk keeps your recovery on track."*

**Selling:** single composite score (Oura playbook) + right-moment nudge (brief's nice-to-have).

### 3. AI Coach chat (0:40 – 1:10)
*"Why is my score down? Let's ask."*

→ Show: coach chat, streaming response: *"Anna, your sleep dropped to 5h 40m the last 3 nights, and your resting heart rate is up 6bpm. Both are recovery signals. Here's what I'd try: [specific action]. [cite wearable data]"*

**Selling:** clinical-grade but consumer-friendly. Grounded in *her* real data.

### 4. NL Record Q&A (1:10 – 1:40) — **the killer moment**
*"Anna has a folder of PDFs she's never read. Let's fix that."*

→ Show: *"What did my last blood test say about cholesterol?"* → Gemini 2.5 Pro pulls from indexed EHR via RAG, answers in plain language: *"Your November panel showed LDL at 138 and ApoB at 112. Both slightly elevated — in Germany the target for someone with your family history is below 90. Here's the actual lab report."* → clickable citation opens the record.

**Selling:** the productivity leap. No other healthcare app does this.

### 5. Risk flag → commercial touchpoint (1:40 – 2:10)
*"And because the AI noticed the ApoB trend, it surfaced this — without an ad banner in sight."*

→ Show: insights card *"Your cardiovascular markers suggest a prevention panel. Our Hamburg cardio-prevention package is covered 80% by your insurance."* → one-tap booking.

**Selling:** monetization without disrupting care. The clinic's unique advantage: real in-network specialists + reimbursement.

### 6. Future-self simulator (2:10 – 2:40) — wow moment
*"And here's what kept Anna engaged."*

→ Show: slider for sleep + activity → animated projection of Vitality Score + biological age at 70, current path vs. improved path.

**Selling:** the nice-to-have from the brief, visualized.

### 7. Architecture flash + close (2:40 – 3:00)
One slide: the API-first architecture diagram from [03-architecture.md](03-architecture.md). 10 seconds.

*"Next.js PWA on every OS today. FastAPI backend on Cloud Run, Frankfurt. Gemini 2.5 via Vertex AI. Cloud SQL with pgvector for the RAG. Every data source is a 50-line adapter — Apple Health and Doctolib are next sprint, not next quarter. GDPR-native, EU-hosted, wellness-framed to stay out of MDR today while we collect the evidence for DiGA reimbursement tomorrow."*

*"One platform. 10 million warm leads. The only longevity app where your doctor actually sees the data. That's our moat."*

## Demo-day contingencies

| If this breaks | Fall back to |
|---|---|
| Gemini API is down | Pre-recorded screen capture of the coach flow |
| Cloud Run cold starts | `--min-instances=1` is set; also local backend as backup |
| Wifi dies | Full local demo via ngrok-free tunnel or pre-recorded video |
| Judge asks "can I try it?" | Hand them the phone with Capacitor wrap installed |
| Judge asks "is this really GDPR-compliant?" | Show the DPIA checklist slide in the appendix |

## Open questions

- Do we build the supplement storefront as a full flow or just a card on the dashboard? Leaning: card only.
- Do we demo on a laptop or phone? Phone is more visceral, laptop is more reliable. **Both** — phone for the demo, laptop mirroring as backup.
