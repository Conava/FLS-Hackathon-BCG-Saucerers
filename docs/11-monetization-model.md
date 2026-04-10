# 11 — Monetization Model

> **Status:** pitch-ready. Supersedes the monetization paragraph in [01-vision.md](01-vision.md) with a defensible, judge-ready three-engine framing. All three engines are already built in the MVP — this doc explains how to *pitch* them, not what to ship.

## TL;DR

Three revenue engines, ranked by defensibility, plus one v2 upside layer. The engines are distinguished by **who pays**, not by what is built:

| # | Engine | Payer | Model | Defensibility |
|---|---|---|---|---|
| 1 | **Longevity+ subscription** | Patient, recurring | €15–25/mo | ~zero CAC on 10M warm leads |
| 2 | **Insurance-billed service routing** | Statutory / private insurance | Reimbursement rails | Owned clinical infrastructure in 9 EU countries |
| 3 | **Out-of-pocket contextual commerce** | Patient, one-off / auto-ship | D2C credit-card checkout | EHR-grounded targeting no D2C app can match |
| v2 | **B2B2C (employer + insurer)** | Corporate contracts | Licensing + risk stratification | 10M-patient longitudinal cohort as training-data moat |

**Back-of-envelope:** 10M × 5% premium × €20/mo × 12 = **€120M ARR** (subscription anchor) + an even 1% fill-rate uplift on the existing €3B business = **+€30M contribution** from engine #2 at ~€0 CAC. Transactional commerce (engine #3) and B2B2C (v2) are pure upside on top.

## Why not just "sell products in the app"?

A pure "advertise/sell the client's products in-app" framing is **necessary but not sufficient**, and if made the headline it actively damages the pitch:

- **Caps upside** at ~2–5% conversion — the same ceiling D2C health apps already hit
- **Erodes clinical trust** — the one moat a hospital group has that no D2C competitor can rebuild
- **Creates MDR framing risk** — ad-driven health recommendations blur the wellness/medical-device line
- **Prices like a lead-gen app**, not like a €3B-business extension

The fix is not to remove commerce. It is to **demote it to engine #3 of 3** and lead with the two engines D2C competitors structurally cannot copy.

## Engine 1 — Longevity+ subscription (€15–25/mo)

**Payer:** the patient, recurring.

The recurring-revenue anchor investors and judges price. Predictable ARR, habit lock-in, and the economic base that subsidises every other engine. Without this, the pitch collapses into "lead-gen app for a hospital group."

**What the subscription unlocks** (already built in the MVP):
- Unlimited AI Coach access
- Quarterly blood panels (routed through engine #2)
- Tele-consults with in-network specialists
- Personalized supplement plan
- Future-self simulator
- Advanced biomarker trendlines in Insights

**Defensibility — the ~zero-CAC argument:**
The client has 10M existing patients with an active clinical relationship. Acquisition is a doctor recommendation at an existing appointment, not a Meta ad. A D2C competitor paying €80–150 CAC to acquire a €240/yr subscriber has a 6–9 month payback. Our payback is **day one**. This single line is worth more than any feature on the slide.

**ARR math:**
10M patients × 5% premium conversion × €20/mo × 12 = **€120M ARR**. Reused from [01-vision.md](01-vision.md) for consistency across the deck.

## Engine 2 — Insurance-billed service routing

**Payer: statutory / private insurance (GKV, PKV, EU equivalents).** Patient pays €0 or a small co-pay.

This is the engine most pitch teams will miss, and it is the one that makes the story defensible at BCG-judge scale. The client already operates **clinics, diagnostics centres, and home care across 9 countries**, with fixed cost bases and idle capacity. The app is not a new product — it is a **demand-routing and fill-rate optimiser** on top of capacity the client is already paying for whether it's used or not.

- Revenue flows through reimbursement rails the client **already owns**
- Incremental contribution margin on a booked slot approaches **100%** (fixed costs are already sunk)
- The patient experiences "the app booked my cardiology appointment" — frictionless, free at point of use
- The client experiences "the app filled 8% more of our existing capacity" — a P&L line item

**Built in the MVP as** the *insurance-billed confirmation* flows in the Care tab: Clinics appointments, most Diagnostics bookings, Home care visits. See the commerce table in [07-features.md](07-features.md).

**Defensibility — the structural moat:**
A D2C startup cannot copy this at any price. Replicating requires:
- Physical clinical infrastructure in 9 countries
- Contracts with statutory payers in every jurisdiction
- Licensed clinicians on payroll
- Decades of reimbursement-code operational knowledge

Ultrahuman cannot do this. Function Health cannot do this. Even Amazon Clinic cannot do this in Europe. This is the engine that separates the clinical-incumbent pitch from the D2C pitch.

**Pitch math:**
*"Even a conservative 1% fill-rate uplift on a €3B business is €30M of near-pure contribution margin at ~€0 customer acquisition cost."* Deliberately understated — judges will push harder the higher the number, so start low and let them argue you up.

## Engine 3 — Out-of-pocket contextual commerce

**Payer:** the patient, direct credit card (one-off or subscription auto-ship).

The D2C-margin layer for things insurance does **not** cover:

- Private diagnostic panels (advanced lipid, microbiome, hormone, food-intolerance kits)
- Private-label supplements on auto-ship (40–60% gross margin)
- 12-week nutrition programs
- At-home test kits
- One-off private coach sessions

**Built in the MVP as** the *credit-card and subscription checkout mocks* in Insights → risk flag → checkout, and in the Care tab's private-coach and private-panel flows. See the commerce table in [07-features.md](07-features.md).

**The rule that protects trust:** commerce is surfaced **when a biomarker moves**, never as banners or ads. The Insights tab's risk flag → contextual offer flow is the canonical path. A D2C app offering you a lipid panel is guessing. Our app offering you a lipid panel is **a signal from your own lab history**, routed through your own doctor's network. That is a qualitatively different product even though the checkout button looks identical.

**Defensibility — EHR-grounded targeting:**
The conversion rate on a commerce CTA tied to a real biomarker movement is categorically higher than the conversion rate on a generic "optimize your health" ad. The 10M-patient EHR history is the substrate. No D2C app has it.

## The difference between engine #2 and engine #3 — and why it matters

Same app, same Care/Insights tabs, two **economically very different** revenue mechanics because the payer is different:

| Attribute | Engine 2 (insurance-billed) | Engine 3 (out-of-pocket) |
|---|---|---|
| Payer | GKV / PKV / statutory | Patient, direct |
| Patient-visible price | €0 or small co-pay | Full price, credit card |
| Revenue route | Existing reimbursement rails | New D2C checkout |
| Margin driver | Incremental utilisation of sunk capacity | Product gross margin (40–60% on supplements) |
| Scaling bottleneck | Physical capacity in 9 countries | Supply chain + fulfillment |
| D2C can copy? | **No** — structural moat | Yes, but without EHR-grounded targeting |
| Pitch role | The unique story no other team will have | The familiar commerce story, with a twist |

Collapsing them into "commerce" loses both arguments. Separating them gives you **two defensible punches instead of one weak one.**

## v2 — B2B2C (employer wellness + insurer risk stratification)

Named as future upside, not v1 revenue. Building it pre-launch dilutes the demo; naming it on the slide unlocks the billion-euro TAM story.

- **Employer wellness contracts** — the client sells the platform to large European employers as a benefit. Corporate contract revenue on top of per-seat licensing.
- **Insurer risk stratification** — longitudinal, de-identified cohort analytics sold to insurers to price risk more accurately. GDPR-safe because it's aggregate, not individual.
- **Cohort data as a training-data moat** — 10M patients × multi-year longitudinal EHR + lifestyle + survey data is a dataset **no startup can replicate at any valuation**. This is the line that turns a €120M ARR story into a €1B+ TAM story.

Keep as a single callout on the monetization slide. Do not build pre-launch.

## What we explicitly reject

Pre-empted on the slide to show consultant thinking before judges raise it:

- **Ad banners / third-party ads.** Trust erosion + MDR framing risk + cheapens the clinical surface. Non-starter.
- **Pay-per-lead referrals to external providers.** Directly undermines the in-network moat, which is the entire point of engine #2.
- **Paywalled AI answers on the patient's own health data.** Looks extractive and invites regulatory and reputational risk. The subscription tier gates *depth and services*, never access to the patient's own records.
- **Freemium data-for-ads (the "if you're not paying, you're the product" model).** Incompatible with a clinical incumbent's trust position.

## Mapping to what is already built

Every engine above is already implemented in the MVP. This doc is a **pitch reframing**, not a build-list.

| Engine | Surfaces already in the MVP | Reference |
|---|---|---|
| 1 — Subscription | Longevity+ tier gating on Coach, Insights, panels, simulator | [07-features.md §commerce](07-features.md) |
| 2 — Insurance-billed routing | Care tab → Clinics, Diagnostics (covered), Home care — confirmation-only flows | [07-features.md §care-tab](07-features.md) |
| 3 — Out-of-pocket commerce | Insights → risk flag → checkout; Care → private coach, private panels; supplement auto-ship | [07-features.md §commerce](07-features.md) |
| v2 — B2B2C | Not built. Named as v2 upside only. | — |

## Summary one-liner for the slide

> **One app. Three engines. €120M ARR from subscription, +€30M fill-rate uplift from routing demand into owned clinics, plus D2C-margin commerce surfaced only when a biomarker moves — all at ~€0 CAC on 10M warm leads. The only longevity platform where the revenue model is as defensible as the product.**
