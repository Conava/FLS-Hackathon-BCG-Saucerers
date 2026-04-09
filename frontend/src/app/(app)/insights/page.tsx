/**
 * Insights screen — server component.
 *
 * Fetches insights from the backend and renders:
 *   1. Header: h1 "Insights" + subtitle "Your four longevity dimensions"
 *   2. 2x2 signal card grid (four longevity dimensions)
 *   3. Risk flag hero card (always shown with demo data)
 *   4. Commercial offer card (demo mock data)
 *   5. Sleep trend bar chart (demo mock data)
 *   6. Future-self simulator (client component, banner scoped inside)
 *   7. Fine-print disclaimer
 *
 * Stack: Next.js 15 App Router, server component, Tailwind v4.
 */

import * as React from "react";
import { backendFetch } from "@/lib/backend-fetch";
import { FutureSelfSimulator } from "./_components/FutureSelfSimulator";
import ScreenFrame from "@/components/shell/ScreenFrame";
import { PageHeader } from "@/components/shell/PageHeader";
import { SectionHeader } from "@/components/design/SectionHeader";

// -- Backend types ------------------------------------------------------------

interface InsightSignal {
  kind: string;
  severity: "low" | "moderate" | "high" | "warn" | "danger";
  label?: string;
  value?: number | string;
  subtext?: string;
  message?: string;
}

interface BackendRiskFlag {
  title: string;
  description: string;
  severity?: string;
}

interface InsightsPayload {
  insights?: InsightSignal[];
  risk_flags?: Array<BackendRiskFlag | string>;
  signals?: InsightSignal[];
}

async function fetchInsights(): Promise<InsightsPayload> {
  try {
    const res = await backendFetch(`/v1/patients/me/insights`, {
      next: { revalidate: 60 },
    });
    if (!res.ok) return {};
    return (await res.json()) as InsightsPayload;
  } catch {
    return {};
  }
}

// -- Signal dimension definitions ---------------------------------------------

interface DimensionDef {
  key: string;
  name: string;
  icon: string;
  fallbackValue: number;
  fallbackSubtext: string;
  fallbackSubtextStatus: "warn" | "good" | "neutral";
}

const DIMENSIONS: DimensionDef[] = [
  {
    key: "biological_age",
    name: "Biological Age",
    icon: "\uD83E\uDDEC",
    fallbackValue: 41,
    fallbackSubtext: "2y younger than chrono",
    fallbackSubtextStatus: "good",
  },
  {
    key: "sleep_recovery",
    name: "Sleep & Recovery",
    icon: "\uD83D\uDE34",
    fallbackValue: 58,
    fallbackSubtext: "3 short nights this week",
    fallbackSubtextStatus: "warn",
  },
  {
    key: "cardio_fitness",
    name: "Cardio Fitness",
    icon: "\u2764\uFE0F",
    fallbackValue: 62,
    fallbackSubtext: "Attention \u00b7 ApoB trending up",
    fallbackSubtextStatus: "warn",
  },
  {
    key: "lifestyle_risk",
    name: "Lifestyle Risk",
    icon: "\uD83C\uDF3F",
    fallbackValue: 74,
    fallbackSubtext: "Steady \u00b7 no alcohol this week",
    fallbackSubtextStatus: "good",
  },
];

// -- Sleep trend mock data ----------------------------------------------------
// demo: replace with real data when endpoint exists

const SLEEP_BARS = [
  { day: "Th", heightPx: 72, color: "var(--color-accent)" },
  { day: "Fr", heightPx: 78, color: "var(--color-accent)" },
  { day: "Sa", heightPx: 68, color: "var(--color-accent)" },
  { day: "Su", heightPx: 80, color: "var(--color-accent)" },
  { day: "Mo", heightPx: 58, color: "var(--color-warn)" },
  { day: "Tu", heightPx: 52, color: "var(--color-warn)" },
  { day: "We", heightPx: 42, color: "var(--color-danger)" },
];

// -- Helpers ------------------------------------------------------------------

function subtextColor(status: "warn" | "good" | "neutral"): string {
  if (status === "warn") return "var(--color-warn)";
  if (status === "good") return "var(--color-good)";
  return "var(--color-ink-3)";
}

// -- Page ---------------------------------------------------------------------

export default async function InsightsPage() {
  const data = await fetchInsights();

  const insightMap = new Map<string, InsightSignal>(
    (data.insights ?? data.signals ?? []).map((ins) => [ins.kind, ins]),
  );

  // Resolve risk flag from backend or use demo default
  const rawFlags = data.risk_flags ?? [];
  const firstFlag =
    rawFlags.length > 0
      ? typeof rawFlags[0] === "string"
        ? {
            title: rawFlags[0] as string,
            description: "",
            severity: "warn",
          }
        : (rawFlags[0] as BackendRiskFlag)
      : null;

  // demo: always show risk flag card (backend flag overrides demo title/desc)
  const riskFlagTitle =
    firstFlag?.title ?? "Your lipid profile is worth a closer look";
  const riskFlagDesc =
    firstFlag?.description ||
    "LDL 3.84 and total cholesterol 7.05 are elevated for your age group, especially given your family history. This is a pattern worth discussing with your doctor.";

  return (
    <ScreenFrame>
      {/* -- 1. Header -------------------------------------------------------- */}
      <PageHeader
        title="Insights"
        subtitle="Your four longevity dimensions"
        mb={14}
      />

      {/* -- 3. Signal grid -------------------------------------------------- */}
      <div
        role="region"
        aria-label="Longevity dimensions"
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: 10,
          marginBottom: 14,
        }}
      >
        {DIMENSIONS.map(
          ({
            key,
            name,
            icon,
            fallbackValue,
            fallbackSubtext,
            fallbackSubtextStatus,
          }) => {
            const insight = insightMap.get(key);
            const displayValue = insight?.value ?? fallbackValue;
            const displaySubtext =
              insight?.subtext ?? insight?.message ?? fallbackSubtext;
            const subtextSt: "warn" | "good" | "neutral" =
              insight?.severity === "low"
                ? "good"
                : insight?.severity === "high" ||
                    insight?.severity === "warn" ||
                    insight?.severity === "danger"
                  ? "warn"
                  : fallbackSubtextStatus;

            const isWarn = subtextSt === "warn";
            const iconBoxBg = isWarn
              ? "var(--color-warn-lt)"
              : "var(--color-accent-lt)";
            const iconBoxColor = isWarn
              ? "var(--color-warn)"
              : "var(--color-accent)";

            return (
              <article
                key={key}
                style={{
                  background: "var(--color-surface)",
                  border: "1px solid var(--color-border)",
                  borderRadius: 14,
                  padding: 12,
                  boxShadow: "var(--shadow-sm)",
                }}
              >
                {/* 28x28 rounded-8 icon container */}
                <div
                  aria-hidden="true"
                  style={{
                    width: 28,
                    height: 28,
                    borderRadius: 8,
                    background: iconBoxBg,
                    color: iconBoxColor,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontSize: 14,
                    marginBottom: 6,
                  }}
                >
                  {icon}
                </div>

                {/* Name: uppercase 11px ink-3 */}
                <p
                  style={{
                    fontSize: 11,
                    fontWeight: 600,
                    color: "var(--color-ink-3)",
                    letterSpacing: "0.04em",
                    textTransform: "uppercase",
                    marginBottom: 2,
                  }}
                >
                  {name}
                </p>

                {/* Value: 20px/800 */}
                <span
                  style={{
                    fontSize: 20,
                    fontWeight: 800,
                    color: "var(--color-ink)",
                    fontVariantNumeric: "tabular-nums",
                    display: "block",
                  }}
                >
                  {displayValue}
                </span>

                {/* Subtext: 11px/600 color-coded */}
                <p
                  style={{
                    fontSize: 11,
                    fontWeight: 600,
                    color: subtextColor(subtextSt),
                    marginTop: 2,
                  }}
                >
                  {displaySubtext}
                </p>
              </article>
            );
          },
        )}
      </div>

      {/* -- 4. Risk flag hero card ------------------------------------------ */}
      <div
        role="alert"
        style={{
          background: "var(--color-surface)",
          border: "1px solid var(--color-border)",
          borderLeft: "4px solid var(--color-warn)",
          borderRadius: 14,
          padding: "14px 16px",
          boxShadow: "var(--shadow-sm)",
          marginBottom: 12,
        }}
      >
        {/* Chip + category label */}
        <div
          style={{
            display: "flex",
            gap: 10,
            alignItems: "center",
            marginBottom: 8,
          }}
        >
          <span
            className="chip chip-warn"
            style={{ display: "inline-flex", alignItems: "center", gap: 5 }}
          >
            <span
              style={{
                width: 6,
                height: 6,
                borderRadius: "50%",
                background: "var(--color-warn)",
                display: "inline-block",
              }}
            />
            Attention
          </span>
          <span style={{ fontSize: 11, color: "var(--color-ink-3)" }}>
            Cardiovascular fitness
          </span>
        </div>

        {/* Title: 15px/700 */}
        <p
          style={{
            fontSize: 15,
            fontWeight: 700,
            color: "var(--color-ink)",
            marginBottom: 4,
          }}
        >
          {riskFlagTitle}
        </p>

        {/* Description: 12.5px/ink-2/line-height 1.55 */}
        <p
          style={{
            fontSize: 12.5,
            color: "var(--color-ink-2)",
            lineHeight: 1.55,
            marginBottom: 12,
          }}
        >
          {riskFlagDesc}
        </p>

        {/* CTA buttons */}
        <div style={{ display: "flex", gap: 8 }}>
          <button
            type="button"
            style={{
              padding: "7px 14px",
              borderRadius: 8,
              background: "var(--color-accent)",
              color: "#fff",
              fontSize: 12,
              fontWeight: 600,
              border: "none",
              cursor: "pointer",
            }}
          >
            Book cardio panel
          </button>
          <button
            type="button"
            style={{
              padding: "7px 14px",
              borderRadius: 8,
              background: "transparent",
              color: "var(--color-accent)",
              fontSize: 12,
              fontWeight: 600,
              border: "1px solid var(--color-accent-md)",
              cursor: "pointer",
            }}
          >
            Ask coach
          </button>
        </div>
      </div>

      {/* -- 5. Commercial offer card ---------------------------------------- */}
      {/* demo: replace with real data when endpoint exists */}
      <div
        style={{
          background:
            "linear-gradient(135deg, var(--color-accent-lt), var(--color-accent-md))",
          border: "1px solid var(--color-accent-md)",
          borderRadius: 14,
          padding: "14px 16px",
          boxShadow: "var(--shadow-sm)",
          marginBottom: 14,
        }}
      >
        {/* Badge: 10.5px/accent-2/uppercase/0.06em */}
        <p
          style={{
            fontSize: 10.5,
            fontWeight: 700,
            color: "var(--color-accent-2)",
            textTransform: "uppercase",
            letterSpacing: "0.06em",
            marginBottom: 4,
          }}
        >
          Recommended for you
        </p>

        {/* Title: 14px/700 */}
        <p
          style={{
            fontSize: 14,
            fontWeight: 700,
            color: "var(--color-ink)",
            marginBottom: 4,
          }}
        >
          Hamburg Cardio-Prevention Package
        </p>

        {/* Subtext with insurance mention */}
        <p
          style={{
            fontSize: 11.5,
            color: "var(--color-ink-2)",
            marginBottom: 10,
            lineHeight: 1.5,
          }}
        >
          Advanced lipid panel + CIMT imaging + cardiologist review.{" "}
          <strong>80% covered by your insurance.</strong>
        </p>

        {/* Price + CTA row */}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          {/* Price: strikethrough 280 + bold 56 20px/800 + "copay" */}
          <div style={{ display: "flex", alignItems: "baseline", gap: 2 }}>
            <span
              style={{
                fontSize: 11,
                textDecoration: "line-through",
                color: "var(--color-ink-3)",
              }}
            >
              &euro;280
            </span>
            <strong
              style={{
                fontSize: 20,
                fontWeight: 800,
                color: "var(--color-ink)",
                marginLeft: 6,
                fontVariantNumeric: "tabular-nums",
              }}
            >
              &euro;56
            </strong>
            <span
              style={{
                fontSize: 11,
                color: "var(--color-ink-3)",
                marginLeft: 4,
              }}
            >
              copay
            </span>
          </div>

          <button
            type="button"
            style={{
              padding: "7px 14px",
              borderRadius: 8,
              background: "var(--color-accent)",
              color: "#fff",
              fontSize: 12,
              fontWeight: 600,
              border: "none",
              cursor: "pointer",
            }}
          >
            Book now
          </button>
        </div>
      </div>

      {/* -- 6. Sleep trend chart -------------------------------------------- */}
      {/* demo: replace with real data when endpoint exists */}
      <SectionHeader
        title="Sleep · last 7 days"
        action={<span className="chip chip-warn">&#x2212;1h avg</span>}
      />

      <div className="card" style={{ marginBottom: 14, padding: "16px 18px" }}>
        {/* Bar chart */}
        <div
          aria-label="Sleep duration chart for last 7 days"
          style={{
            display: "flex",
            alignItems: "flex-end",
            justifyContent: "space-between",
            gap: 6,
            height: 90,
          }}
        >
          {SLEEP_BARS.map(({ day, heightPx, color }) => (
            <div
              key={day}
              style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                gap: 4,
              }}
            >
              <div
                style={{
                  width: 22,
                  background: color,
                  borderRadius: 4,
                  height: heightPx,
                }}
              />
              <span style={{ fontSize: 10, color: "var(--color-ink-3)" }}>
                {day}
              </span>
            </div>
          ))}
        </div>

        {/* Summary */}
        <p
          style={{
            fontSize: 11.5,
            color: "var(--color-ink-2)",
            marginTop: 10,
            lineHeight: 1.5,
          }}
        >
          Avg <strong>6h 32m</strong> &middot; target 7h 30m. Your wearable
          data shows a pattern worth acting on.
        </p>
      </div>

      {/* -- 7. Future-self simulator ---------------------------------------- */}
      <FutureSelfSimulator />

      {/* -- 8. Fine print --------------------------------------------------- */}
      <p className="t-fine" style={{ marginTop: 16, paddingTop: 4 }}>
        Projections are illustrative wellness guidance, not disease prediction.
      </p>
    </ScreenFrame>
  );
}
