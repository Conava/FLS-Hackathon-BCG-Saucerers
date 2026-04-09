/**
 * Today screen — Server Component.
 *
 * Data fetching strategy (per task spec):
 *   Read `patient_id` from the httpOnly cookie and call the FastAPI backend
 *   directly at `BACKEND_URL/v1/patients/{id}/...`.
 *   Client components still use the `/api/proxy` route via the typed api client.
 *
 * Five fetches run in parallel via Promise.all.
 *
 * Stack: Next.js 15 App Router — params / cookies are async APIs.
 */

import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import Link from "next/link";
import {
  AiDisclosureBanner,
  OutlookCurve,
  StreakBadge,
  SectionHeader,
  NudgeCard,
  MacroRing,
  EmptyState,
} from "@/components/design";
import { VitalityTap } from "./_components/VitalityTap";
import { ProtocolList } from "./_components/ProtocolList";
import { COPY } from "@/lib/copy/copy";
import { backendFetch } from "@/lib/backend-fetch";
import type {
  PatientProfileOut,
  VitalityOut,
  OutlookOut,
  ProtocolOut,
  InsightsListOut,
  MealLogListOut,
} from "@/lib/api/schemas";

// ---------------------------------------------------------------------------
// Server-side direct fetch helpers
// ---------------------------------------------------------------------------

/**
 * Fetch a JSON endpoint from the FastAPI backend directly.
 * Should only be called from Server Components.
 * Uses backendFetch to inject the X-API-Key header.
 */
async function backendGet<T>(
  patientId: string,
  path: string,
): Promise<T | null> {
  try {
    const res = await backendFetch(`/v1/patients/${patientId}/${path}`);
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Compute a delta score from the vitality trend (last two points).
 * Returns 0 if there are fewer than two trend points.
 */
function computeDelta(vitality: VitalityOut): number {
  const trend = vitality.trend ?? [];
  if (trend.length < 2) return 0;
  const last = trend[trend.length - 1]?.score ?? vitality.score;
  const prev = trend[trend.length - 2]?.score ?? vitality.score;
  return Math.round(last - prev);
}

/**
 * Extract a streak (max streak_days across all protocol actions).
 */
function computeStreak(protocol: ProtocolOut | null): number {
  if (!protocol?.actions?.length) return 0;
  return Math.max(...protocol.actions.map((a) => a.streak_days ?? 0));
}

/**
 * Build outlook curve points from OutlookOut.
 * Generates 9 interpolated points for a smooth sparkline, or [] if no data.
 * Uses a slight S-curve easing so the line looks natural.
 */
function buildOutlookPoints(
  vitality: VitalityOut | null,
  outlook: OutlookOut | null,
): number[] {
  if (!vitality || !outlook) return [];
  const current = vitality.score;
  const projected = outlook.projected_score;
  const numPoints = 9;
  return Array.from({ length: numPoints }, (_, i) => {
    const t = i / (numPoints - 1);
    // Ease-in-out cubic: smooth S-curve from current to projected
    const eased = t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
    return current + (projected - current) * eased;
  });
}

/**
 * Find the most urgent insight — prefer "high", then "moderate".
 */
function findUrgentInsight(insights: InsightsListOut | null) {
  const list = insights?.insights ?? [];
  return (
    list.find((i) => i.severity === "high") ??
    list.find((i) => i.severity === "moderate") ??
    null
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default async function TodayPage() {
  // 1. Read patient_id from cookie — redirect to /login if absent
  const cookieStore = await cookies();
  const patientId = cookieStore.get("patient_id")?.value;
  if (!patientId) {
    redirect("/login");
  }

  // 2. Parallel fetch all required data
  const today = new Date().toISOString().slice(0, 10);
  const [profile, vitality, outlookList, protocol, insights, mealLogs] =
    await Promise.all([
      backendGet<PatientProfileOut>(patientId, "profile"),
      backendGet<VitalityOut>(patientId, "vitality"),
      // Backend returns list[OutlookOut] (one per horizon: 3, 6, 12 months).
      backendGet<OutlookOut[]>(patientId, "outlook"),
      backendGet<ProtocolOut>(patientId, "protocol"),
      backendGet<InsightsListOut>(patientId, "insights"),
      backendGet<MealLogListOut>(patientId, `meal-log?from=${today}&to=${today}`),
    ]);

  // Pick the 6-month outlook horizon, falling back to the largest available.
  const outlook: OutlookOut | null = Array.isArray(outlookList) && outlookList.length > 0
    ? (outlookList.find((o) => o.horizon_months === 6) ??
       outlookList.reduce((best, cur) =>
         cur.horizon_months > best.horizon_months ? cur : best
       ))
    : null;

  // 3. Derive display values
  // "Patient PT0199" → skip the generic "Patient" placeholder; use the last
  // non-"Patient" word, or fall back to empty string so the greeting reads
  // "Good morning" without an awkward placeholder.
  const nameParts = (profile?.name ?? "").trim().split(/\s+/).filter(Boolean);
  const meaningfulName =
    nameParts.length > 1 && nameParts[0]?.toLowerCase() === "patient"
      ? (nameParts[nameParts.length - 1] ?? "")
      : (nameParts[0] ?? "");
  const firstName = meaningfulName || "";
  const score = vitality?.score ?? 0;
  const delta = vitality ? computeDelta(vitality) : 0;
  const streak = computeStreak(protocol);
  const outlookPoints = buildOutlookPoints(vitality, outlook);
  const actions = protocol?.actions ?? [];
  const urgentInsight = findUrgentInsight(insights);
  const insightsList = insights?.insights ?? [];

  // 4. Compute macro ring values from today's meal logs
  const todayLog = mealLogs?.logs?.[0] ?? null;
  type MacroKey = "protein_g" | "fiber_g" | "polyphenol_score" | "alcohol_units";
  const macros: Record<MacroKey, number> = {
    protein_g:
      typeof todayLog?.analysis?.macros?.protein_g === "number"
        ? (todayLog.analysis.macros.protein_g as number)
        : 0,
    fiber_g:
      typeof todayLog?.analysis?.macros?.fiber_g === "number"
        ? (todayLog.analysis.macros.fiber_g as number)
        : 0,
    polyphenol_score:
      typeof todayLog?.analysis?.macros?.polyphenol_score === "number"
        ? (todayLog.analysis.macros.polyphenol_score as number)
        : 0,
    alcohol_units:
      typeof todayLog?.analysis?.macros?.alcohol_units === "number"
        ? (todayLog.analysis.macros.alcohol_units as number)
        : 0,
  };

  return (
    <div
      style={{
        padding: "8px 20px 28px",
        display: "flex",
        flexDirection: "column",
        gap: 0,
        maxWidth: 480,
        margin: "0 auto",
      }}
    >
      {/* ── Header ─────────────────────────────────────────────────────── */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: 10,
        }}
      >
        <div>
          <p className="t-caption text-ink-3">
            {COPY.today.greeting(firstName)}
          </p>
          <h1
            className="t-h1 text-ink"
            style={{ lineHeight: 1.2, marginTop: 2 }}
          >
            {new Date().toLocaleDateString("en-GB", {
              weekday: "short",
              day: "numeric",
              month: "short",
            })}
          </h1>
        </div>
      </div>

      {/* AI Disclosure Banner — required on AI-powered screens */}
      <AiDisclosureBanner />

      {/* ── Hero card: Vitality ring + streak + outlook ─────────────────── */}
      <div
        className="bg-surface shadow-app-sm"
        style={{
          borderRadius: 20,
          border: "1px solid var(--color-border)",
          padding: 18,
          marginTop: 12,
          textAlign: "center",
        }}
      >
        {/* Row: "Vitality Score" label + streak badge */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            marginBottom: 4,
          }}
        >
          <span
            className="t-micro text-ink-3"
            style={{ letterSpacing: "0.06em" }}
          >
            Vitality Score
          </span>
          {streak > 0 && <StreakBadge days={streak} />}
        </div>

        {/* Vitality ring — centered, tappable */}
        <div style={{ display: "flex", justifyContent: "center" }}>
          {vitality ? (
            <VitalityTap
              score={score}
              delta={delta}
              insights={insightsList}
            />
          ) : (
            <EmptyState
              heading="Vitality score unavailable"
              subtext="We could not compute your score yet. Check back after syncing more data."
            />
          )}
        </div>

        {/* Outlook narrative text */}
        {outlook?.narrative && (
          <p
            className="t-caption text-ink-2"
            style={{ marginTop: 8, padding: "0 8px" }}
          >
            {outlook.narrative}
          </p>
        )}

        {/* Outlook curve — immediately below the ring */}
        {outlookPoints.length >= 2 && (
          <OutlookCurve
            points={outlookPoints}
            nowLabel={`Now · ${Math.round(score)}`}
            endLabel={`${outlook?.horizon_months ?? 6}mo · ${Math.round(outlook?.projected_score ?? outlookPoints[outlookPoints.length - 1] ?? score)}`}
          />
        )}
      </div>

      {/* ── Nudge Card (conditional) ─────────────────────────────────────── */}
      {urgentInsight && (
        <div style={{ marginTop: 14 }}>
          <NudgeCard
            title={urgentInsight.kind
              .replace(/_/g, " ")
              .replace(/\b\w/g, (c) => c.toUpperCase())}
            description={urgentInsight.message}
            ctaLabel="Learn more"
          />
        </div>
      )}

      {/* ── Today's Protocol ─────────────────────────────────────────────── */}
      <div style={{ marginTop: 20 }}>
        <SectionHeader title="Today's protocol" />
        <ProtocolList actions={actions} />
      </div>

      {/* ── Nutrition Today (Macro Rings) ─────────────────────────────────── */}
      <div style={{ marginTop: 20 }}>
        <SectionHeader
          title="Nutrition rings"
          action={
            <Link
              href="/meal-log"
              className="t-support text-accent font-semibold"
            >
              Log a meal
            </Link>
          }
        />

        {todayLog ? (
          <div
            className="bg-surface shadow-app-sm"
            style={{
              borderRadius: 20,
              border: "1px solid var(--color-border)",
              padding: 18,
            }}
          >
            <div
              style={{
                display: "flex",
                gap: 14,
                justifyContent: "space-around",
              }}
            >
              <MacroRing
                nutrient="protein"
                value={macros.protein_g}
                target={50}
                label="Protein"
              />
              <MacroRing
                nutrient="fiber"
                value={macros.fiber_g}
                target={30}
                label="Fiber"
              />
              <MacroRing
                nutrient="polyphenols"
                value={macros.polyphenol_score}
                target={100}
                label="Polyphenols"
              />
              <MacroRing
                nutrient="alcohol"
                value={macros.alcohol_units}
                target={14}
                label="Alcohol"
              />
            </div>
          </div>
        ) : (
          <EmptyState
            heading={COPY.today.noActivity}
            subtext="Log a meal to see your nutrition rings."
            action={
              <Link
                href="/meal-log"
                className="t-support font-semibold text-accent"
                style={{
                  padding: "8px 16px",
                  borderRadius: 999,
                  background: "var(--color-accent-lt)",
                  textDecoration: "none",
                }}
              >
                Log a meal
              </Link>
            }
          />
        )}
      </div>

      {/* Fine print */}
      <p
        className="t-legal text-ink-3"
        style={{ textAlign: "center", marginTop: 14, padding: "0 12px" }}
      >
        Not medical advice. Wellness and lifestyle guidance only.
      </p>
    </div>
  );
}
