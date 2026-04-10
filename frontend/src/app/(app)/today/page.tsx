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
  OutlookCurve,
  StreakBadge,
  SectionHeader,
  NudgeCard,
  MacroRing,
  EmptyState,
} from "@/components/design";
import { VitalityTap } from "./_components/VitalityTap";
import { ProtocolList } from "./_components/ProtocolList";
import { QuickLogGrid } from "./_components/QuickLogGrid";
import { WeeklyCheckInCard } from "./_components/WeeklyCheckInCard";
import { RecentlyCard } from "./_components/RecentlyCard";
import { COPY } from "@/lib/copy/copy";
import { backendFetch } from "@/lib/backend-fetch";
import ScreenFrame from "@/components/shell/ScreenFrame";
import { PageHeader } from "@/components/shell/PageHeader";
import type {
  PatientProfileOut,
  VitalityOut,
  OutlookOut,
  ProtocolOut,
  InsightsListOut,
  MealLogListOut,
  SurveyHistoryOut,
  EHRRecordListOut,
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
 * Build outlook curve points combining past trend (from vitality.trend)
 * and a future projection toward outlook.projected_score.
 *
 * Result layout:
 *   [past_0, past_1, ..., past_n-1, now, future_1, ..., future_8]
 *
 * The returned `nowIndex` tells the renderer where "today" sits on the x-axis
 * so past points render dimmer and future points render in accent colour.
 *
 * If vitality.trend is empty, falls back to a future-only 9-point S-curve
 * (original behaviour).
 */
function buildOutlookPoints(
  vitality: VitalityOut | null,
  outlook: OutlookOut | null,
): { points: number[]; nowIndex: number } {
  if (!vitality || !outlook) return { points: [], nowIndex: 0 };

  const current = vitality.score;
  const projected = outlook.projected_score;

  // Vitality.trend is returned newest-first by the backend — reverse to
  // oldest-first for plotting. Cap at 14 past points so the sparkline is
  // legible (matches roughly a two-week lookback).
  const rawTrend = vitality.trend ?? [];
  const pastScores = rawTrend
    .slice(0, 14)
    .map((p) => p.score)
    .reverse();

  // Build 8 future points ramping from current → projected with ease-in-out.
  // (The "now" point is shared with the end of the past segment.)
  const futureCount = 8;
  const futurePoints = Array.from({ length: futureCount }, (_, i) => {
    const t = (i + 1) / futureCount;
    const eased = t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
    return current + (projected - current) * eased;
  });

  if (pastScores.length === 0) {
    // No past data — fall back to future-only 9-point S-curve.
    const points = [current, ...futurePoints];
    return { points, nowIndex: 0 };
  }

  const points = [...pastScores, current, ...futurePoints];
  const nowIndex = pastScores.length;
  return { points, nowIndex };
}

/**
 * Build a contextual sentence headline for a nudge card from an insight kind
 * and severity. Avoids bare category labels like "Metabolic".
 *
 * Examples:
 *   "metabolic"      + "high"     → "Elevated metabolic signal — act today"
 *   "sleep"          + "moderate" → "Watch your sleep pattern"
 *   "cardiovascular" + "high"     → "Elevated cardiovascular signal — act today"
 */
function buildNudgeTitle(kind: string, severity: string): string {
  const label = kind.replace(/_/g, " ").toLowerCase();
  if (severity === "high") {
    return `Elevated ${label} signal — act today`;
  }
  return `Watch your ${label} pattern`;
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

/**
 * Format today's date as "Today · Wed 9 Apr".
 */
function formatTodayTitle(date: Date): string {
  const weekday = date.toLocaleDateString("en-GB", { weekday: "short" });
  const day = date.getDate();
  const month = date.toLocaleDateString("en-GB", { month: "short" });
  return `Today · ${weekday} ${day} ${month}`;
}

/**
 * Extract meaningful first name — skips generic "Patient PT0199" placeholders.
 */
function extractFirstName(fullName: string | undefined): string {
  const nameParts = (fullName ?? "").trim().split(/\s+/).filter(Boolean);
  const meaningfulName =
    nameParts.length > 1 && nameParts[0]?.toLowerCase() === "patient"
      ? (nameParts[nameParts.length - 1] ?? "")
      : (nameParts[0] ?? "");
  return meaningfulName || "";
}

/**
 * Compute initials (up to 2 chars) for the avatar button.
 */
function getInitials(fullName: string | undefined): string {
  const parts = (fullName ?? "").trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "Me";
  if (parts.length === 1) return (parts[0]?.slice(0, 2) ?? "Me").toUpperCase();
  return `${parts[0]?.[0] ?? ""}${parts[parts.length - 1]?.[0] ?? ""}`.toUpperCase();
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
  const [
    profile,
    vitality,
    outlookList,
    protocol,
    insights,
    mealLogs,
    surveyHistory,
    labRecords,
  ] = await Promise.all([
    backendGet<PatientProfileOut>(patientId, "profile"),
    backendGet<VitalityOut>(patientId, "vitality"),
    // Backend returns list[OutlookOut] (one per horizon: 3, 6, 12 months).
    backendGet<OutlookOut[]>(patientId, "outlook"),
    backendGet<ProtocolOut>(patientId, "protocol"),
    backendGet<InsightsListOut>(patientId, "insights"),
    backendGet<MealLogListOut>(patientId, `meal-log?from=${today}&to=${today}`),
    backendGet<SurveyHistoryOut>(patientId, "survey/history?kind=weekly&limit=1"),
    // Lab records for the Recently card — most recent lab_panel (ordered DESC).
    backendGet<EHRRecordListOut>(patientId, "records?type=lab_panel"),
  ]);

  // Pick the 6-month outlook horizon, falling back to the largest available.
  const outlook: OutlookOut | null =
    Array.isArray(outlookList) && outlookList.length > 0
      ? (outlookList.find((o) => o.horizon_months === 6) ??
          outlookList.reduce((best, cur) =>
            cur.horizon_months > best.horizon_months ? cur : best,
          ))
      : null;

  // Derive the most recent lab_panel record for the Recently card.
  const latestLab =
    Array.isArray(labRecords?.records) && labRecords.records.length > 0
      ? (labRecords.records[0] ?? null)
      : null;

  // 3. Derive display values
  const firstName = extractFirstName(profile?.name);
  const initials = getInitials(profile?.name);
  const score = vitality?.score ?? 0;
  const delta = vitality ? computeDelta(vitality) : 0;
  const streak = computeStreak(protocol);
  const { points: outlookPoints, nowIndex: outlookNowIndex } =
    buildOutlookPoints(vitality, outlook);
  const actions = protocol?.actions ?? [];
  const urgentInsight = findUrgentInsight(insights);
  const insightsList = insights?.insights ?? [];

  // Weekly check-in: compute days since last submission
  const lastCheckIn = surveyHistory?.responses?.[0]?.submitted_at ?? null;
  const daysSinceLastCheckIn: number | null = lastCheckIn
    ? Math.floor(
        (Date.now() - new Date(lastCheckIn).getTime()) / (1000 * 60 * 60 * 24),
      )
    : null;

  // Protocol progress
  const doneCount = actions.filter((a) => a.completed_today).length;
  const totalCount = actions.length;

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

  const todayTitle = formatTodayTitle(new Date());

  return (
    <ScreenFrame>
      {/* ── Header ─────────────────────────────────────────────────────── */}
      <PageHeader
        title={todayTitle}
        subtitle={COPY.today.greeting(firstName)}
        mb={10}
        trailing={
          <Link
            href="/me"
            aria-label="Profile"
            style={{
              width: 28,
              height: 28,
              borderRadius: "50%",
              background: "var(--color-accent)",
              color: "#fff",
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 11,
              fontWeight: 700,
              textDecoration: "none",
            }}
          >
            {initials}
          </Link>
        }
      />

      {/* ── Hero card: Vitality ring + streak + outlook ─────────────────── */}
      <div
        className="card"
        style={{
          marginTop: 10,
          textAlign: "center",
        }}
      >
        {/* Row: "VITALITY SCORE" label + streak badge */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            marginBottom: 4,
          }}
        >
          <span className="t-micro">
            Vitality Score
          </span>
          {streak > 0 && <StreakBadge days={streak} />}
        </div>

        {/* Vitality ring — centered, tappable */}
        <div style={{ display: "flex", justifyContent: "center" }}>
          {vitality ? (
            <VitalityTap
              score={Math.round(score)}
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
            style={{
              fontSize: 12,
              color: "var(--color-ink-2)",
              marginTop: 8,
              padding: "0 8px",
              lineHeight: 1.5,
            }}
          >
            {outlook.narrative}
          </p>
        )}

        {/* Outlook curve — immediately below the ring */}
        {outlookPoints.length >= 2 && (
          <OutlookCurve
            points={outlookPoints}
            nowIndex={outlookNowIndex}
            nowLabel={`Now · ${Math.round(score)}`}
            endLabel={`${
              outlook?.horizon_months === 6
                ? "Oct"
                : `${outlook?.horizon_months ?? 6}mo`
            } · ${Math.round(
              outlook?.projected_score ??
                outlookPoints[outlookPoints.length - 1] ??
                score,
            )}`}
          />
        )}
      </div>

      {/* ── Nudge Card (conditional — only when there is a high/moderate insight) ── */}
      {urgentInsight && (
        <div style={{ marginTop: 14 }}>
          <NudgeCard
            title={buildNudgeTitle(urgentInsight.kind, urgentInsight.severity)}
            description={urgentInsight.message}
            ctaLabel="View in coach"
            secondaryLabel="Dismiss"
          />
        </div>
      )}

      {/* ── Today's Protocol ─────────────────────────────────────────────── */}
      <div style={{ marginTop: 14 }}>
        <SectionHeader
          title="Today's protocol"
          action={
            totalCount > 0 ? (
              <span className="chip chip-muted">
                {doneCount} / {totalCount} done
              </span>
            ) : undefined
          }
        />
        <ProtocolList actions={actions} />
      </div>

      {/* ── Quick Log — 4-col grid ─────────────────────────────────────────── */}
      <div style={{ marginTop: 14 }}>
        <SectionHeader title="Quick log" />
        <QuickLogGrid />
      </div>

      {/* ── Nutrition Today (Macro Rings) ─────────────────────────────────── */}
      <div style={{ marginTop: 14 }}>
        <SectionHeader
          title="Nutrition rings"
          action={
            <span className="chip chip-good">
              <span
                style={{
                  width: 6,
                  height: 6,
                  borderRadius: "50%",
                  background: "currentColor",
                  display: "inline-block",
                }}
              />
              On track
            </span>
          }
        />

        <div className="card">
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
      </div>

      {/* ── Recently — latest lab + score change ─────────────────────────── */}
      <div style={{ marginTop: 14 }}>
        <SectionHeader title="Recently" />
        <RecentlyCard latestLab={latestLab} vitality={vitality} />
      </div>

      {/* ── Weekly micro-survey card ──────────────────────────────────────── */}
      <WeeklyCheckInCard daysSinceLastCheckIn={daysSinceLastCheckIn} />

      {/* Fine print */}
      <p
        className="t-fine"
        style={{
          marginTop: 14,
          padding: "0 12px",
        }}
      >
        Not medical advice. Wellness and lifestyle guidance only.
      </p>
    </ScreenFrame>
  );
}
