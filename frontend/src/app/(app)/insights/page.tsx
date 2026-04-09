/**
 * Insights screen — server component.
 *
 * Fetches insights from the backend via BACKEND_URL (server-side fetch),
 * renders four SignalCard longevity dimension cards, any RiskFlag cards,
 * then the client-side FutureSelfSimulator.
 *
 * Stack: Next.js 15 App Router, server component, Tailwind v4.
 */

import * as React from "react";
import { SignalCard, RiskFlag } from "@/components/design";
import { COPY } from "@/lib/copy/copy";
import { FutureSelfSimulator } from "./_components/FutureSelfSimulator";
import { backendFetch } from "@/lib/backend-fetch";

interface InsightItem {
  kind: string;
  severity: "low" | "moderate" | "high";
  message: string;
}

interface InsightsPayload {
  insights?: InsightItem[];
  risk_flags?: string[];
  signals?: string[];
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

function severityToTrend(
  severity: "low" | "moderate" | "high",
): "up" | "down" | "neutral" {
  if (severity === "low") return "up";
  if (severity === "high") return "down";
  return "neutral";
}

function severityToStatus(
  severity: "low" | "moderate" | "high",
): "good" | "warn" | "neutral" {
  if (severity === "low") return "good";
  if (severity === "high") return "warn";
  return "neutral";
}

/** The four fixed longevity dimension signal cards. */
const DIMENSION_KEYS = [
  { key: "biological_age", label: "Biological Age", icon: "\uD83E\uDDEC" },
  { key: "sleep_recovery", label: "Sleep & Recovery", icon: "\uD83D\uDE34" },
  { key: "cardio_fitness", label: "Cardio Fitness", icon: "\uD83D\uDC93" },
  { key: "lifestyle_risk", label: "Lifestyle Risk", icon: "\u26A0\uFE0F" },
] as const;

export default async function InsightsPage() {
  const data = await fetchInsights();

  const insightMap = new Map<string, InsightItem>(
    (data.insights ?? []).map((ins) => [ins.kind, ins]),
  );

  return (
    <main
      style={{ display: "flex", flexDirection: "column", gap: 24, padding: "0 0 32px" }}
    >
      <header style={{ padding: "16px 0 0" }}>
        <h1 className="t-heading-lg text-ink">{COPY.insights.title}</h1>
        <p className="t-caption text-ink-3" style={{ marginTop: 4 }}>
          {COPY.insights.subtitle}
        </p>
      </header>

      <section aria-label="Longevity dimensions">
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: 12,
          }}
        >
          {DIMENSION_KEYS.map(({ key, label, icon }) => {
            const insight = insightMap.get(key);
            return (
              <SignalCard
                key={key}
                label={label}
                value={insight ? insight.severity.toUpperCase() : "\u2014"}
                subText={insight?.message}
                status={insight ? severityToStatus(insight.severity) : "neutral"}
                trend={insight ? severityToTrend(insight.severity) : "neutral"}
                icon={<span style={{ fontSize: 14 }}>{icon}</span>}
              />
            );
          })}
        </div>
      </section>

      {(data.risk_flags ?? []).length > 0 && (
        <section aria-label="Flagged Risks">
          <h2
            className="t-heading-sm text-ink"
            style={{ marginBottom: 12 }}
          >
            Flagged Risks
          </h2>
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {(data.risk_flags ?? []).map((flag, i) => (
              <RiskFlag
                key={i}
                title={flag}
                description={COPY.insights.disclosure}
                level="warn"
              />
            ))}
          </div>
        </section>
      )}

      <FutureSelfSimulator />
    </main>
  );
}
