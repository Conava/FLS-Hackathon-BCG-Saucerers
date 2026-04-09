# 02 — Persona, Journey & User Stories

> **Status:** LOCKED. Grounded in real data from the provided dataset. Primary demo patient: **PT0282**. Secondary cameo: **PT0421**.

## Primary persona — Anna Weber

**43, product manager, Hamburg. Married, two kids (8 and 11). Private insurance. Long-standing patient of the clinic group — her whole family has gone there for 15 years.**

> **Backed by real data:** Anna's profile is grounded in patient **PT0282** from `ehr_records.csv` — 43F, German, BMI 22.7, ex-smoker, no active chronic diagnoses. On paper she looks healthy. Her labs tell a quieter story: **total cholesterol 7.05 mmol/L, LDL 3.84 mmol/L, SBP 128** — hidden cardiovascular risk the AI surfaces. This is the **preventive longevity thesis**: looks fine, isn't fine.

### Backstory
Last year her dad had a mild heart attack at 68. It wasn't fatal, but it shook her. She started reading about longevity, bought a Fitbit, downloaded MyFitnessPal, and has a folder of PDFs from her last check-up she never opened because they're full of medical jargon.

### Motivations
- Be healthy and present for her kids when they're 30
- Understand her own cardiovascular risk (genetic component scares her)
- Stop feeling tired by 3pm every day
- Make sense of her health data without a 30-minute Google spiral

### Fears
- Inheriting her dad's heart condition
- Wasting money and time on wellness fads (she's skeptical of influencer supplements)
- Losing control of her health data to random apps
- Missing an early warning sign she could have acted on

### Frustrations with today's status quo
- Her GP has 8 minutes per visit and doesn't have time for prevention conversations
- Lab results come as PDFs in medical jargon — no plain-language summary
- Nobody connects the dots between her sleep, stress, and bloodwork
- US longevity apps (Function, Lifeforce) aren't available in Germany and she wouldn't trust them with her kids' records anyway

### Why she trusts the clinic
- 15-year relationship, her GP knows her family history
- German data protection, not a startup
- If something's wrong, a real doctor is a tram ride away

## Longevity journey map

From first awareness to daily engagement. Each stage is a hook we design for.

| Stage | Trigger | What Anna does | What the app does | Touchpoint |
|---|---|---|---|---|
| **Awareness** | Dad's heart attack | Googles "heart attack risk women 40s" | — | Organic, clinic newsletter |
| **Activation** | Clinic emails her: "See your Vitality Score" | Signs in with existing patient account | Pulls EHR + asks 3 lifestyle questions | Web / PWA install |
| **First insight** | Dashboard loads | Sees Vitality Score + 2 personalized recommendations | Synthesizes EHR + wearable + survey into one score | Dashboard |
| **First action** | Coach nudges: "You slept 5h 40m — skip HIIT today" | Changes plan | Tracks adherence | Coach, notifications |
| **First aha moment** | Asks "What did my last blood test say about cholesterol?" | Gets plain-language answer citing the actual record | NL Q&A over her EHR via RAG | Records view |
| **First commercial** | AI flags ApoB trending up | Taps "book cardio-prevention panel" | Surfaces diagnostic package + books into clinic calendar | Insights + appointments |
| **Habit formation** | Daily score + streak | Opens app most mornings | Personalized nudges at learned optimal times | Push / in-app |
| **Deep engagement** | Asks the coach hard questions | Treats coach as prevention advisor | Cites evidence, escalates to human clinician when needed | Coach |
| **Commercial deep** | Subscribes to Longevity+ | Quarterly panels, supplement plan | Auto-ships, books follow-ups | Subscription |
| **Advocate** | Refers sister | — | Referral program | Shareable Vitality Score snapshot |

## User stories

Written in "As a / I want / So that" format. These ground prototype decisions.

### Must-have stories

**US-1 — Unified view**
> As Anna, I want to see my clinical data, wearable data, and lifestyle inputs in one place, so that I don't have to mentally merge three apps and a folder of PDFs.

**US-2 — Plain-language record Q&A**
> As Anna, I want to ask natural-language questions about my own medical records and get answers citing the actual documents, so that I understand my health without decoding jargon or waiting for a GP appointment.

**US-3 — Right-moment nudge**
> As Anna, I want the app to nudge me with a specific action at the moment I can actually do something about it, so that advice becomes behavior instead of another ignored notification.

**US-4 — Risk-to-action path**
> As Anna, I want early warning signals surfaced with a one-tap path to a real doctor in my network, so that I'm not left to Google "is ApoB 120 bad" at 11pm.

### Nice-to-have stories

**US-5 — Future-self simulator**
> As Anna, I want to see a projection of my health at 70 based on current habits vs. improved habits, so that I'm motivated by a concrete picture instead of abstract advice.

**US-6 — Flexible appointments**
> As Anna, I want to book appointments with my clinic *or* external specialists (via Doctolib etc.), so that the app stays useful even when I need someone outside the network.

## Secondary cameo — PT0421

A 10-second supporting mention in the pitch, not a full persona. Shows the system works for patients across the risk spectrum, not just the worried well.

**45F, Germany, BMI 28.9, current smoker, diagnosed hypertension (I10), on Amlodipine 5mg/day**
- BP **140/108** despite medication (Stage 2 hypertension — meds aren't controlling it)
- Total cholesterol **6.63**, LDL 3.75, HDL 1.23 (low), CRP 2.4, HbA1c 5.7% (pre-diabetic edge), eGFR 61 (mildly reduced)
- Wearable: **sleep quality trended from 75 down to 59** over 90 days while duration held at 7.2h — fragmented, non-restorative sleep
- Only 1.8 fruit/veg servings/day, 2 exercise sessions/week

**Pitch use:** *"And our system isn't just for the worried well — here's PT0421, a patient whose hypertension has been uncontrolled despite therapy for two years. Our coach flagged both the BP trend and the degrading sleep quality on day one."* Also: her sleep-trend chart is dramatic, use it as the hero visual in the analytics screen.

## Anna's data story (pitch-ready, from real numbers)

> Anna came to us worried about her heart after her father's infarct last year. On paper she's fine — she's lean (BMI 22.7), an ex-smoker, no diagnoses, 43 years old. But her last lab panel tells a quieter story: total cholesterol **7.05 mmol/L** and LDL **3.84 mmol/L** — both meaningfully elevated for a woman her age with family history. Her blood pressure at 128 is borderline. For two years, nobody connected the dots between these numbers and her anxiety about her dad's heart attack. Our AI coach did — on the first screen. It flagged the lipid profile, pulled her family history from the EHR, and surfaced a cardio-prevention panel from our Hamburg clinic — one tap to book, 80% covered by her insurance. Anna didn't know she was at risk until we showed her. That's the longevity product.

## Open questions

- None for persona itself. Journey-level open questions: do we need a second persona (older, diagnosed) for the pitch, or does the PT0421 cameo carry that angle?
