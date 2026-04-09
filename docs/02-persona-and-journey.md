# 02 — Persona, Journey & User Stories

> **Status:** LOCKED. Grounded in real data from the provided dataset. Primary demo patient: **PT0199**. Secondary cameo: **PT0421**.

## Primary persona — Rebecca Mueller

**40, part-time HR consultant, Hamburg. Married, two young kids (3 and 5). Statutory health insurance (gesetzlich versichert). Patient of the clinic group for 5 years — since the birth of her first child.**

> **Backed by real data:** Rebecca's profile is grounded in patient **PT0199** from `ehr_records.csv` — 40F, BMI 27.6, ex-smoker, diagnosed Type 2 diabetes (E11), on Metformin 1000 mg twice daily. Her labs reinforce the risk picture: **HbA1c 7.2 %, fasting glucose 12.4 mmol/L, total cholesterol 5.68 mmol/L, LDL 3.72 mmol/L, CRP 2.4 mg/L, eGFR 68, SBP 142 mmHg**. She is slightly overweight, sleeping poorly, stressed — and until now, nobody has connected those dots. This is the **whole-person longevity thesis**: the numbers are there, the lifestyle signals are there, but no one is joining them up.
>
> *Note: PT0199 is coded as Austria in the dataset. For the persona we relocate Rebecca to Hamburg; all clinical values are used as-is.*

### Backstory
On her 40th birthday, Rebecca bent down to pick something up and felt a sharp sting of pain surge through her lower back and up her spine. That single moment cracked open a bigger realisation: she had roughly 40 years left, and the second half of her life was going to get progressively harder — physically and mentally — if she didn't change course now.

The back pain was the trigger for a clinic visit, but the fear ran deeper. In the months before, she had noticed that simple things — playing on the floor with her 3-year-old, chasing her 5-year-old at the park, staying present during family evenings instead of zoning out from exhaustion — had become noticeably harder. She was tired all the time, her sleep was broken, and her Type 2 diabetes diagnosis (about a year old) felt like a ticking clock she didn't know how to manage beyond taking her Metformin.

### Motivations
- Live the second half of her life healthily — not just longer, but *better*
- Make good memories with her kids, her husband, and her friends while she still has energy
- Feel physically fit enough to keep up with two small children
- Get her diabetes, weight, and stress under control in a way that actually sticks
- Stop feeling like her body is declining faster than it should at 40

### Fears
- That the tiredness and pain she feels now is just the beginning of a slow decline
- That her diabetes will spiral into complications she can't reverse
- Wasting money on wellness trends that don't work (she's a pragmatist — skeptical of influencer supplements and miracle diets)
- Losing control of her health data to random apps — though her fear of her own health trajectory makes her more open to trying something her doctor actually recommends
- Missing an early warning sign she could have acted on

### Frustrations with today's status quo
- Her GP has 8 minutes per visit and doesn't have time for prevention conversations — the diabetes gets checked, but her sleep, stress, energy, and weight are treated as separate problems
- Lab results come as PDFs in medical jargon — no plain-language summary, no connection to daily life
- Nobody connects the dots between her broken sleep, her rising HbA1c, her stress at work, and her back pain
- US longevity apps (Function, Lifeforce) aren't available in Germany, and she wouldn't trust them with her family's data anyway

### Why she trusts the clinic
- 5-year relationship, built since the birth of her first child — they know her family
- German data protection, not a startup
- Her doctor personally recommended the app during the back-pain visit
- If something's wrong, a real doctor is a tram ride away

## Longevity journey map

From first awareness to daily engagement. Each stage is a hook we design for.

| Stage | Trigger | What Rebecca does | What the app does | Touchpoint |
|---|---|---|---|---|
| **Awareness** | 40th birthday back-pain episode | Visits her trusted clinic about the back pain; notices posters in the waiting room about a new longevity product | — | In-clinic posters, leaflets |
| **Activation** | Doctor recommends the app during consultation | Downloads the app out of curiosity and fear; signs in with existing patient account | Pulls EHR + asks 3 lifestyle questions (sleep, stress, activity) | Web / PWA install |
| **First insight** | Dashboard loads | Sees Vitality Score + 2 personalised recommendations connecting her sleep, weight, and HbA1c | Synthesises EHR + wearable (Apple Watch) + survey into one score | Dashboard |
| **First action** | Coach nudges: "Your sleep was 5 h 20 m — try a 10-min wind-down tonight" | Follows the suggestion, sleeps slightly better | Tracks adherence, adjusts next nudge | Coach, notifications |
| **First aha moment** | Asks "Why am I always tired even though I sleep 7 hours?" | Gets a plain-language answer linking her fragmented sleep, HbA1c, and cortisol pattern | NL Q&A over her EHR via RAG | Records view |
| **Positive feedback loop** | Sees her sleep score improve after 10 days of nudges | Thinks: "I can actually commit to this" | Reinforces with streak + micro-celebration | Dashboard, push |
| **First commercial** | AI flags HbA1c trending up + fasting glucose elevated | Taps "book diabetes & metabolic panel" | Surfaces diagnostic package + books into clinic calendar | Insights + appointments |
| **Habit formation** | Daily score + streak | Opens app most mornings before the kids wake up | Personalised nudges at learned optimal times | Push / in-app |
| **Deep engagement** | Asks the coach hard questions about diabetes progression | Treats coach as prevention advisor | Cites evidence, escalates to human clinician when needed | Coach |
| **Commercial deep** | Subscribes to Longevity+ | Quarterly panels, supplement plan | Auto-ships, books follow-ups | Subscription |
| **Advocate** | Refers a colleague who also just turned 40 | — | Referral program | Shareable Vitality Score snapshot |

## User stories

Written in "As a / I want / So that" format. These ground prototype decisions.

### Must-have stories

**US-1 — Unified view**
> As Rebecca, I want to see my clinical data, wearable data, and lifestyle inputs in one place, so that I don't have to mentally merge three apps and a folder of PDFs.

**US-2 — Plain-language record Q&A**
> As Rebecca, I want to ask natural-language questions about my own medical records and get answers citing the actual documents, so that I understand my health without decoding jargon or waiting for a GP appointment.

**US-3 — Right-moment nudge**
> As Rebecca, I want the app to nudge me with a specific action at the moment I can actually do something about it, so that advice becomes behaviour instead of another ignored notification.

**US-4 — Risk-to-action path**
> As Rebecca, I want early warning signals surfaced with a one-tap path to a real doctor in my network, so that I'm not left to Google "is HbA1c 7.2 bad" at 11 pm.

### Nice-to-have stories

**US-5 — Future-self simulator**
> As Rebecca, I want to see a projection of my health at 70 based on current habits vs. improved habits, so that I'm motivated by a concrete picture instead of abstract advice.

**US-6 — Flexible appointments**
> As Rebecca, I want to book appointments with my clinic *or* external specialists (via Doctolib etc.), so that the app stays useful even when I need someone outside the network.

## Secondary cameo — PT0421

A 10-second supporting mention in the pitch, not a full persona. Shows the system works for patients across the risk spectrum, not just the worried well.

**45F, Germany, BMI 28.9, current smoker, diagnosed hypertension (I10), on Amlodipine 5 mg/day**
- BP **140/108** despite medication (Stage 2 hypertension — meds aren't controlling it)
- Total cholesterol **6.63**, LDL 3.75, HDL 1.23 (low), CRP 2.4, HbA1c 5.7 % (pre-diabetic edge), eGFR 61 (mildly reduced)
- Wearable: **sleep quality trended from 75 down to 59** over 90 days while duration held at 7.2 h — fragmented, non-restorative sleep
- Only 1.8 fruit/veg servings/day, 2 exercise sessions/week

**Pitch use:** *"And our system isn't just for the worried well — here's PT0421, a patient whose hypertension has been uncontrolled despite therapy for two years. Our coach flagged both the BP trend and the degrading sleep quality on day one."* Also: her sleep-trend chart is dramatic, use it as the hero visual in the analytics screen.

## Rebecca's data story (pitch-ready, from real numbers)

> Rebecca came to us after her 40th birthday — not because of a diagnosis, but because of a sting of pain in her lower back that made her realise her body was changing faster than she expected. On paper she's "managing" — she has a Type 2 diabetes diagnosis, she takes her Metformin, she sees her GP. But her last lab panel tells a bigger story: **HbA1c 7.2 %** (above target despite medication), **fasting glucose 12.4 mmol/L** (significantly elevated), **total cholesterol 5.68 mmol/L and LDL 3.72 mmol/L** (both raised), **CRP 2.4 mg/L** (low-grade inflammation), **eGFR 68** (early renal signal worth watching), and **blood pressure at 142 mmHg systolic** — nobody had flagged the emerging hypertension. She sleeps poorly, she's exhausted by 3 pm, she can barely keep up with a 3-year-old and a 5-year-old. For a year, each of these problems was treated in isolation — diabetes here, tiredness there, back pain somewhere else. Our AI coach connected them on the first screen. It linked the sleep disruption to her glycaemic control, flagged the blood pressure trend, pulled her weight and activity data from her Apple Watch, and surfaced a metabolic health panel from our Hamburg clinic — one tap to book, covered by her GKV. Rebecca didn't know how much risk she was carrying until we showed her the whole picture. That's the longevity product.
