# 07 — Feature Scope & Demo Flow

What we build, what we fake, what we defer, and the exact 3-minute story we tell on stage.

## Product shape in one paragraph

A mobile-first PWA structured around **five personal-language tabs** (Today, Coach, Records, Insights, Care) plus a **Me** profile icon. Every tab maps to either a daily engagement loop, a personalized AI surface, or a commercial touchpoint back into the healthcare group's real service portfolio (clinics, diagnostics centres, home care). Nutrition is woven across every surface rather than siloed. A **Protocol + Streak engine** turns Coach recommendations into daily actions and powers a forward-looking **Vitality Outlook**. A **Survey loop** (onboarding + weekly micro + quarterly deep) keeps the AI grounded in ground-truth that wearables can't capture.

## Information architecture

Five tabs + one profile icon. Personal-language labels, not feature names.

| Tab | Role | What lives here |
|---|---|---|
| **Today** | Daily return hook + self-tracking | Vitality Score, Vitality Outlook, streak / WALR counter, 3–7 daily protocol actions, nudge-of-the-day, quick-log (meal photo, mood, workout, sleep, water) |
| **Coach** | General personalized AI | Conversational coach; personalized via wearable + survey + EHR context; can suggest actions that write back to Today's protocol; nutrition advice + recipes + meal planning |
| **Records** | Official provider data | EHR, labs, imaging, medications, allergies; plain-language Q&A scoped **strictly** to provider records with clickable citations |
| **Insights** | Analytical lens + commerce | Four longevity dimensions (see below), risk & opportunity flags, biomarker trendlines, **Future-self simulator** (merged here), contextual commerce CTAs |
| **Care** | Human-in-the-loop + physical services | Appointments and bookings across the three service pillars: **Clinics**, **Diagnostics centres**, **Home care**; clinician reviews; messages to care team |
| **Me** *(icon)* | Profile & control | Profile, **Survey (retake)**, data sources, consents, notifications, privacy, delete-my-data |

**Why personal-language labels:** judging criteria reward consumer-product polish. "Today" sells better than "Dashboard", "Care" sells better than "Book".

## Four longevity dimensions (structural backbone)

The brief lists four "exemplary" longevity dimensions. We adopt them as the explicit structure of the Vitality Score, the Signals drill-down, and the Insights risk-flag taxonomy. Using the brief's own framing is cheap alignment points with judges.

1. **Biological Age** — physiological aging vs. chronological age
2. **Sleep & Recovery Profiling** — rest, recovery, regeneration
3. **Cardiovascular Fitness** — heart/circulatory efficiency and endurance
4. **Lifestyle & Behavioral Risk** — everyday habits shaping long-term outcomes

Every risk flag, biomarker card, and nutrition correlation is tagged with one of these four. Tapping the Vitality Score on Today drills into a **Signals** view with one card per dimension.

## Vitality Score, Outlook, and Future-self — three time horizons, one language

| Horizon | Name | What drives it | Where it lives |
|---|---|---|---|
| Now | **Vitality Score** | Biomarkers + wearable + baseline survey (objective, slow-moving) | Today (hero), Signals drill-down |
| Near-term (3 / 6 / 12 mo) | **Vitality Outlook** | **Streak momentum** on the daily protocol — holding streaks projects the outlook curve upward; breaking them flattens (never punitively drops) | Today (secondary), Insights |
| Long-term (10+ yr) | **Future-self simulator** | Lifestyle sliders (sleep, activity, nutrition, alcohol) → projected biological age + score at 70 | Insights |

This gives the user a coherent narrative: *"Your score is 68 today. Hold your current streak and your outlook reaches 74 by October. If you sustain it for a decade, your biological age at 70 is 64 instead of 71."* Three horizons, one visual language, one pitch beat.

## Protocol + Streak engine

The north-star metric (WALR — Weekly Actioned Longevity Recommendations ≥3/week) finally has a home.

- **Protocol** = 3–7 daily actions auto-generated weekly by Coach from the user's goals, biomarkers, survey, and recent signals. Editable by the user. Coach can nudge mid-week if data warrants ("you slept 5h — swap HIIT for a walk today").
- Each action carries: category (movement / sleep / nutrition / mind / supplement), target, one-line rationale linking back to Coach, quick-log button.
- **Self-tracking** = one-tap complete, plus quick-logs for meals (photo → Gemini vision), mood, workouts, sleep (if no wearable), water, alcohol.
- **Streaks** = per-action and overall. Visible on Today. Feed the Vitality Outlook curve — holding a streak nudges the outlook upward; breaking it flattens. Never punitive.
- **Score feedback loop:** completed actions do **not** directly move the current Vitality Score (that stays objective). They move the **Outlook** and, sustained over weeks, feed back into the slow-moving Score via biomarker improvement. This keeps the model defensible: *"your score rose because the biomarkers moved, and the biomarkers moved because you actually did the things."*

## Nutrition — woven in, not siloed

Nutrition is explicitly one of the three commercial touchpoint categories in the brief ("health checks, diagnostic packages, or nutritional offerings"). We treat it as a first-class citizen across every surface rather than a dedicated tab.

| Surface | Nutrition role |
|---|---|
| **Today** | Meal quick-log (**photo → Gemini vision → macros + longevity swap**), daily protein/fiber/polyphenol rings, one featured meal swap, alcohol tracking |
| **Coach** | Meal planning, recipes, pre-workout fueling, "what should I eat to move my ApoB down?" |
| **Records** | Allergies, food intolerances, relevant labs (vitamin D, B12, lipid panel, HbA1c) |
| **Insights** | Nutrition-linked biomarker correlations ("your HRV drops on high-alcohol weeks"), nutrition-driven risk flags, **nutrition program** commerce CTA |
| **Care** | Dietitian booking (clinic), **at-home microbiome kit** (diagnostics + home care) |
| **Me** | Dietary pattern, restrictions, allergies, cooking willingness, alcohol baseline |

**Demo moment for nutrition:** photograph a plate → Gemini vision classifies + estimates macros → one-line longevity-optimized swap ("swap the white rice for lentils — +12g fiber, same calories, better postprandial glucose"). Cheap to build, highly demoable.

## Care tab — mirrors the company's real service portfolio

The brief describes the client as operating **clinics, diagnostics centres, and home care services**. The Care tab is explicitly structured around those three pillars so the app visibly mirrors the business it's pitching to.

| Pillar | Examples | Billing model in demo |
|---|---|---|
| **Clinics** | GP, cardiologist, dietitian, physio appointments; specialist referrals; in-network-only priority slots | Insurance-billed — confirmation screen, no checkout |
| **Diagnostics centres** | Lab panels (lipid, advanced lipid, HbA1c, CBC), imaging (DEXA, CIMT), at-home test kits (microbiome, food-intolerance) | Mix: insurance-billed or **credit-card checkout mock** (one-time) |
| **Home care** | In-home phlebotomy, nurse visits, at-home physio, post-op care | Insurance-billed or **checkout mock** (co-pay) |

Plus: **clinician review** surface ("Dr. Lehmann reviewed your ApoB flag · follow-up booked"), **messages to care team**, and **referral program** (journey stage 10 from the persona doc — finally has a home).

## Commerce — checkout mocks where they're authentic

Per the rule "physical services are often insurance-billed, not credit-card":

| Surface | Flow | Checkout type |
|---|---|---|
| Insights → diagnostic panel | One-time purchase, ships home or scheduled at centre | **Credit-card mock** |
| Insights → supplement stack | Monthly auto-ship, cancelable | **Subscription mock** |
| Insights → nutrition program | 12-week coaching program | **Credit-card mock** |
| Care → Clinics appointment | In-network specialist | Insurance-billed confirmation |
| Care → Diagnostics panel | Lab or imaging | Insurance-billed *or* credit-card mock depending on coverage |
| Care → Home care visit | In-home service | Insurance-billed with optional co-pay field |
| Care → Private coach session | One-off 60-min | **Credit-card mock** |

Three real credit-card flows + two subscription/one-time mixes + authentic insurance framings. More convincing than making everything a credit-card flow.

## Survey loop

The pivotal grounding mechanism for recommendations — and the only way users without wearables still get personalized protocols.

### Onboarding (3 min, ~12 questions)
- Primary longevity goal (live longer / feel better / manage a condition / performance)
- Motivators & fears (reuse persona doc taxonomy)
- **Motivation type** (aesthetics / performance / disease-avoidance / longevity-curious) — tunes Coach tone
- Sleep: typical hours, subjective quality 1–5, wake-ups
- Activity: sessions/week, intensity, modalities
- **Nutrition: diet pattern (omnivore / vegetarian / vegan / low-carb / Mediterranean / other), meals/day, ultra-processed frequency, cooking willingness, known intolerances/allergies**
- **Alcohol** units/week, **caffeine** cups/day
- Stress 1–5, social connection 1–5
- **Time budget per day** for protocol actions (prevents over-prescribing)
- **Out-of-pocket budget** per month (gates commerce — no €400 panels recommended to someone with a €50 ceiling)
- Constraints (injuries, dietary restrictions, medications)
- Data sources willing to connect

### Weekly micro-survey (30 sec, 3 questions, contextually prompted from Today)
- "How did this week feel?" (energy 1–5)
- "Anything change?" (stress / sleep / new meds / travel / injury — chips)
- "Protocol fit?" (too easy / right / too hard) — feeds protocol re-generation

### Quarterly deep retake (5 min)
- Full re-survey with side-by-side Score / Outlook deltas
- Goal re-setting
- **Natural commerce moment:** *"Your ApoB outlook stalled — consider the Advanced Lipid panel"*

### Storage strategy
Survey answers are stored **both** as typed structured fields (drives the protocol generator, commerce gating, nutrition rings) **and** as embedded free-text chunks (RAG-able by Coach for nuanced retrieval).

## Build state

The checkboxes below track the product scope commitment, not implementation completeness. For implementation status:

**Backend slice 1 — done:** unified patient profile ingestion, vitality score + sub-scores, EHR/wearable/insights/appointments/GDPR read endpoints, API-key auth, CI.

**Backend slice 2 — done:** Full `/v1` API — 26 endpoints, LLM abstraction (FakeLLMProvider/GeminiProvider), pgvector RAG, SSE coach streaming, protocol generator, meal vision, outlook engine + narrator, future-self simulator, survey loop (onboarding/weekly/quarterly), DailyLog, MealLog with photo storage (local + GCS), notifications (LLM-generated copy), clinical review, referral, messages. GDPR delete now removes MealLog rows and photo files. Committed `backend/openapi.json`.

**Frontend — not yet started.** The mockup (`mockup/index.html`) is the UI contract.

## Must-have (from the brief + our extension)

From the BCG brief:
- [x] **AI health coach** with personal, evidence-grounded recommendations
- [x] **Risk and opportunity flagging** with actionable interventions
- [x] **In-app commercial touchpoints** — diagnostics, packages, supplements, **nutrition programs** surfaced contextually

From our product thinking:
- [x] **Unified patient profile** — EHR + wearable + lifestyle + survey in one place
- [x] **Vitality Score + Outlook** — composite daily-return hook with streak-driven forward projection
- [x] **Four-dimension Signals drill-down** — Biological Age, Sleep & Recovery, Cardio Fitness, Lifestyle & Behavioral Risk
- [x] **Protocol + Streak engine** — daily actions, self-tracking, WALR counter
- [x] **Survey loop** — onboarding + weekly micro + quarterly deep retake
- [x] **Coach (general AI)** and **Records Q&A (EHR-scoped)** as separate surfaces
- [x] **Nutrition woven across Today / Coach / Insights / Care / Me** — including meal-photo vision logging
- [x] **Care tab structured around clinics / diagnostics centres / home care** — mirrors the client's portfolio
- [x] **Future-self simulator** nested inside Insights (not a standalone tab)
- [x] **Commerce checkout mocks** for diagnostic panel, supplement subscription, nutrition program, private coach session
- [x] **Multi-OS** — PWA works on web + iOS + Android + desktop; Capacitor wrap demonstrates native story

## Nice-to-have (build if time permits after core flow works)

- [x] **Clinician review card** — backend stub persists `ClinicalReview` rows; `GET/POST /v1/patients/{pid}/clinical-review`
- [x] **Referral program** — backend stub persists `Referral` rows; `GET/POST /v1/patients/{pid}/referral`
- [x] **Messages to care team** — `GET/POST /v1/patients/{pid}/messages`
- [x] **Weekly micro-survey prompt** — survey router supports `kind=weekly`; `POST /v1/patients/{pid}/survey`
- [ ] **Signals drill-down** — four-dimension cards under Vitality Score (frontend only)
- [ ] **At-home test-kit checkout** (microbiome / food-intolerance)

## Deferred (mentioned in pitch, not built)

- Real Doctolib / Jameda OAuth integration (mocked)
- Actual Apple Health / Fitbit API wiring (stubbed via adapter layer)
- Native iOS + Android builds (Capacitor wrap is a 1h showcase, not a shipped binary)
- Push notification infrastructure (in-app banners in demo)
- Auth / multi-tenant (demo uses a pre-loaded patient)
- DiGA certification (v2 track)
- Full consent management UI beyond onboarding toggles
- Real biological-age model (demo uses a transparent heuristic — sleep, HRV, VO2max proxy, ApoB)

## The 3-minute demo script

Rehearsed until flawless. Every screen earns its spot by selling one pillar of the pitch.

### Setup (pre-demo, not on stage)
Browser tabbed to the PWA. Rebecca's account pre-loaded: 40yo, Type 2 diabetes on Metformin, elevated HbA1c and fasting glucose, 5 nights of poor sleep, Apple Watch connected, onboarding survey completed, 6-day protocol streak.

### 1. Onboarding story (0:00 – 0:20)
*"Meet Rebecca. 40, part-time HR consultant in Hamburg. On her 40th birthday, a sting of back pain made her realise the second half of her life needed a different approach. She's a patient of our clinic network. Her doctor recommended the app during her next visit."*

→ Show: one-click login, 3-question lifestyle micro-form (subset of full survey for demo speed), **instant score reveal**.

**Selling:** zero-friction activation. 10M warm leads → no CAC.

### 2. Today (0:20 – 0:45)
*"This is Rebecca's morning. One number, one outlook, one action."*

→ Show: Vitality Score 68 (down from 74), **Vitality Outlook** curve projecting to 74 by October if the streak holds, 6-day streak badge, today's protocol (3 actions: walk 25 min, lights-out 22:30, swap rice for lentils at lunch), nudge: *"You slept 5h 40m. Skip HIIT today — a 25-min walk keeps your recovery on track."*

**Selling:** single composite score + forward-looking outlook + streak-driven engagement + right-moment nudge. Three time horizons in one screen.

### 3. AI Coach chat (0:45 – 1:10)
*"Why is my score down? Let's ask."*

→ Show: Coach chat, streaming response: *"Rebecca, your sleep dropped to 5h 20m the last 3 nights, and your resting heart rate is up 6bpm. Both are recovery signals — and fragmented sleep can raise your fasting glucose. Try tonight: 22:00 lights out, no alcohol, 300mg magnesium glycinate. I've added these to today's protocol."* → actions appear on Today.

**Selling:** clinical-grade but consumer-friendly. Grounded in *her* real data. Writes back to the protocol loop.

### 4. Nutrition moment — meal photo (1:10 – 1:25)
*"Rebecca's at lunch."*

→ Show: camera → photo of a plate → Gemini vision classifies (grilled salmon, white rice, broccoli) → macro estimation → **longevity swap suggestion**: *"Swap white rice for lentils — +12g fiber, same calories, lower postprandial glucose."* → one-tap log to Today's protein/fiber rings.

**Selling:** nutrition woven in. The brief's third commercial category, made visceral.

### 5. Records Q&A (1:25 – 1:50) — **the killer moment**
*"Rebecca has a folder of PDFs she's never read. Let's fix that."*

→ Show: *"What did my last blood test say about cholesterol?"* → Gemini 2.5 Pro pulls from indexed EHR via RAG, answers in plain language: *"Your last panel showed total cholesterol at 5.68 mmol/L and LDL at 3.72 mmol/L — both elevated, especially given your diabetes. Your HbA1c is 7.2%, above target despite Metformin. Here's the actual lab report."* → clickable citation opens the record.

**Selling:** the productivity leap. No other healthcare app does this. Records stays scoped strictly to provider data — distinct from Coach.

### 6. Insights → risk flag → commercial touchpoint (1:50 – 2:15)
*"And because the AI noticed the metabolic trend, it surfaced this — without an ad banner in sight."*

→ Show: Insights tab opens on the four-dimension Signals view; Lifestyle & Behavioral Risk card is flagged amber. Tap → risk detail → *"Your HbA1c and fasting glucose suggest a metabolic health panel. Our Hamburg diabetes & metabolic package is covered by your GKV."* → one-tap route to Care → Diagnostics checkout.

**Selling:** monetization without disrupting care. The clinic's unique advantage: real in-network specialists + reimbursement. Commerce mirrors the company's diagnostics-centre business.

### 7. Future-self simulator (2:15 – 2:40) — wow moment
*"And here's what kept Rebecca engaged."*

→ Still in Insights, scroll to Future-self. Slider for sleep + activity + alcohol → animated projection of Vitality Score + biological age at 70, current path vs. improved path.

**Selling:** the long-horizon third time-scale. Nested in Insights alongside the near-term outlook — one analytical lens, two horizons.

### 8. Architecture flash + close (2:40 – 3:00)
One slide: the API-first architecture diagram from [03-architecture.md](03-architecture.md). 10 seconds.

*"Next.js PWA on every OS today. FastAPI backend on Cloud Run, Frankfurt. Gemini 2.5 via Vertex AI. Cloud SQL with pgvector for the RAG. Every data source is a 50-line adapter — Apple Health and Doctolib are next sprint, not next quarter. GDPR-native, EU-hosted, wellness-framed to stay out of MDR today while we collect the evidence for DiGA reimbursement tomorrow."*

*"One platform. 10 million warm leads. Clinics, diagnostics centres, and home care all in the same app. The only longevity app where your doctor actually sees the data. That's our moat."*

## Demo-day contingencies

| If this breaks | Fall back to |
|---|---|
| Gemini API is down | Pre-recorded screen capture of the coach + records + nutrition flows |
| Gemini vision (meal photo) fails | Pre-loaded meal log with the swap suggestion already cached |
| Cloud Run cold starts | `--min-instances=1` is set; also local backend as backup |
| Wifi dies | Full local demo via ngrok-free tunnel or pre-recorded video |
| Judge asks "can I try it?" | Hand them the phone with Capacitor wrap installed |
| Judge asks "is this really GDPR-compliant?" | Show the DPIA checklist slide in the appendix |
| Judge asks "how is this different from Oura / Whoop?" | *"They sell a ring. We sell the outcome — and your doctor is in the loop."* |

## Open questions

- Does the Signals drill-down (four-dimension cards) live on Today under the score, or inside Insights? Leaning: **both** — compact summary on Today, full detail in Insights.
- Do we demo the meal-photo flow live or pre-cache it? Leaning: **pre-cache** — Gemini vision latency is the one thing we can't control on stage.
- Weekly micro-survey: demo it as a contextual card, or skip for the 3-minute story? Leaning: **skip for demo, keep in the build** — it's a retention feature, not a wow feature.
