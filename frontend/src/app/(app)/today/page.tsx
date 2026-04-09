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
  const outlook: OutlookOut | null =
    Array.isArray(outlookList) && outlookList.length > 0
      ? (outlookList.find((o) => o.horizon_months === 6) ??
          outlookList.reduce((best, cur) =>
            cur.horizon_months > best.horizon_months ? cur : best,
          ))
      : null;

  // 3. Derive display values
  const firstName = extractFirstName(profile?.name);
  const initials = getInitials(profile?.name);
  const score = vitality?.score ?? 0;
  const delta = vitality ? computeDelta(vitality) : 0;
  const streak = computeStreak(protocol);
  const outlookPoints = buildOutlookPoints(vitality, outlook);
  const actions = protocol?.actions ?? [];
  const urgentInsight = findUrgentInsight(insights);
  const insightsList = insights?.insights ?? [];

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
          <p
            style={{ fontSize: 13, fontWeight: 500, color: "var(--color-ink-3)" }}
          >
            {COPY.today.greeting(firstName)}
          </p>
          <h1
            style={{
              fontSize: 22,
              fontWeight: 700,
              letterSpacing: "-0.01em",
              lineHeight: 1.2,
              marginTop: 2,
              color: "var(--color-ink)",
            }}
          >
            {todayTitle}
          </h1>
        </div>

        {/* Avatar button — 28px circle, accent bg, white initials, links to /me */}
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
            flexShrink: 0,
          }}
        >
          {initials}
        </Link>
      </div>

      {/* ── Hero card: Vitality ring + streak + outlook ─────────────────── */}
      <div
        className="card"
        style={{
          marginTop: 12,
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
          <span
            style={{
              fontSize: 11,
              fontWeight: 700,
              color: "var(--color-ink-3)",
              textTransform: "uppercase",
              letterSpacing: "0.06em",
            }}
          >
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
            title={urgentInsight.kind
              .replace(/_/g, " ")
              .replace(/\b\w/g, (c) => c.toUpperCase())}
            description={urgentInsight.message}
            ctaLabel="Add walk to protocol"
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

      {/* ── Weekly micro-survey card ──────────────────────────────────────── */}
      <div
        className="card"
        style={{
          marginTop: 14,
          background: "var(--color-accent-lt)",
          borderColor: "var(--color-accent-md)",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 8,
          }}
        >
          <div>
            <p
              style={{
                fontSize: 12,
                fontWeight: 700,
                color: "var(--color-accent)",
                textTransform: "uppercase",
                letterSpacing: "0.06em",
              }}
            >
              30-sec check-in
            </p>
            <p
              style={{
                fontSize: 11.5,
                color: "var(--color-ink-2)",
                marginTop: 2,
              }}
            >
              How did this week feel?
            </p>
          </div>
          <button
            type="button"
            style={{
              padding: "8px 12px",
              borderRadius: 14,
              background: "var(--color-accent)",
              color: "#fff",
              fontSize: 12.5,
              fontWeight: 600,
              border: "none",
              cursor: "pointer",
              minHeight: 36,
              flexShrink: 0,
            }}
          >
            Start
          </button>
        </div>
      </div>

      {/* Fine print */}
      <p
        style={{
          fontSize: 10.5,
          color: "var(--color-ink-3)",
          textAlign: "center",
          marginTop: 14,
          padding: "0 12px",
          lineHeight: 1.5,
        }}
      >
        Not medical advice. Wellness and lifestyle guidance only.
      </p>
    </div>
  );
}
