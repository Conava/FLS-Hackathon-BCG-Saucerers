/**
 * RecentlyCard — server-rendered "What changed recently" card.
 *
 * Displays two history rows inside a single card:
 *   1. Most recent lab result (lab_panel EHR record)
 *   2. Latest vitality score change (derived from trend points)
 *
 * All data is passed in as props — no client state, no hooks.
 * Renders gracefully with empty-state rows when either data source is absent.
 */

import * as React from "react";
import type { EHRRecordOut } from "@/lib/api/schemas";
import type { VitalityOut } from "@/lib/api/schemas";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface RecentlyCardProps {
  /** Most recent lab_panel EHR record, or null if none available. */
  latestLab: EHRRecordOut | null;
  /** Vitality data (used to derive score delta from trend). */
  vitality: VitalityOut | null;
}

// ---------------------------------------------------------------------------
// Lab row helpers
// ---------------------------------------------------------------------------

/** Lab panel payload keys that carry a notable risk signal when elevated. */
const LAB_SIGNAL_THRESHOLDS: {
  key: string;
  label: string;
  unit: string;
  warnAbove?: number;
  goodBelow?: number;
}[] = [
  { key: "ldl_mmol", label: "LDL", unit: "mmol/L", warnAbove: 3.4 },
  { key: "total_cholesterol_mmol", label: "Chol", unit: "mmol/L", warnAbove: 5.2 },
  { key: "hba1c_pct", label: "HbA1c", unit: "%", warnAbove: 5.7 },
  { key: "crp_mg_l", label: "CRP", unit: "mg/L", warnAbove: 3.0 },
  { key: "fasting_glucose_mmol", label: "Glucose", unit: "mmol/L", warnAbove: 5.6 },
  { key: "triglycerides_mmol", label: "Trigs", unit: "mmol/L", warnAbove: 1.7 },
  { key: "hdl_mmol", label: "HDL", unit: "mmol/L", goodBelow: 1.0 },
];

interface LabChipInfo {
  label: string;
  variant: "warn" | "danger" | "good" | "muted";
}

/**
 * Find the most notable value in a lab_panel payload and return a chip label
 * plus color variant. Returns "Reviewed" + muted if no standout found.
 */
function extractLabChip(
  payload: Record<string, unknown>
): LabChipInfo {
  for (const sig of LAB_SIGNAL_THRESHOLDS) {
    const raw = payload[sig.key];
    if (typeof raw !== "number") continue;

    // HDL is protective — flag as warn when LOW
    if (sig.goodBelow !== undefined && raw < sig.goodBelow) {
      return {
        label: `${sig.label} ${raw.toFixed(1)} ${sig.unit}`,
        variant: "warn",
      };
    }
    // Other markers — flag as warn when HIGH
    if (sig.warnAbove !== undefined && raw > sig.warnAbove) {
      const variant: LabChipInfo["variant"] =
        sig.key === "hba1c_pct" && raw > 6.5 ? "danger" : "warn";
      return {
        label: `${sig.label} ${raw.toFixed(1)} ${sig.unit}`,
        variant,
      };
    }
  }

  return { label: "Reviewed", variant: "muted" };
}

/**
 * Format a date string as "Mon YYYY" (e.g. "Nov 2025").
 */
function formatMonthYear(isoDate: string): string {
  try {
    const d = new Date(isoDate);
    return d.toLocaleDateString("en-GB", { month: "short", year: "numeric" });
  } catch {
    return "";
  }
}

/**
 * Extract a human-readable title from a lab_panel record.
 * Looks for a "panel_name" or "title" key in payload, falls back to "Lipid panel".
 */
function extractLabTitle(payload: Record<string, unknown>): string {
  if (typeof payload.panel_name === "string") return payload.panel_name;
  if (typeof payload.title === "string") return payload.title;
  return "Lipid panel";
}

// ---------------------------------------------------------------------------
// Score row helpers
// ---------------------------------------------------------------------------

interface ScoreDeltaInfo {
  delta: number;
  prev: number;
  current: number;
  /** ISO date string of the previous trend point */
  prevDate: string;
}

/**
 * Derive a score delta from the vitality trend array.
 * Returns null if the trend has fewer than 2 points.
 */
function extractScoreDelta(vitality: VitalityOut): ScoreDeltaInfo | null {
  const trend = vitality.trend ?? [];
  if (trend.length < 2) return null;
  const last = trend[trend.length - 1];
  const prev = trend[trend.length - 2];
  if (!last || !prev) return null;
  return {
    delta: Math.round(last.score - prev.score),
    prev: Math.round(prev.score),
    current: Math.round(last.score),
    prevDate: String(prev.date),
  };
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

/** 32×32 icon container — pill with a background color and emoji content. */
function IconContainer({
  bg,
  children,
}: {
  bg: string;
  children: React.ReactNode;
}) {
  return (
    <div
      aria-hidden="true"
      style={{
        width: 32,
        height: 32,
        borderRadius: 10,
        background: bg,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontSize: 16,
        flexShrink: 0,
      }}
    >
      {children}
    </div>
  );
}

type ChipVariant = "warn" | "danger" | "good" | "muted";
const CHIP_STYLES: Record<ChipVariant, React.CSSProperties> = {
  warn: { background: "var(--color-warn-lt)", color: "var(--color-warn)" },
  danger: { background: "var(--color-danger-lt)", color: "var(--color-danger)" },
  good: { background: "var(--color-good-lt)", color: "var(--color-good)" },
  muted: { background: "var(--color-bg-2)", color: "var(--color-ink-3)" },
};

/** Small status chip with semantic coloring. */
function HistoryChip({
  label,
  variant,
}: {
  label: string;
  variant: ChipVariant;
}) {
  return (
    <span
      style={{
        ...CHIP_STYLES[variant],
        padding: "4px 9px",
        borderRadius: 999,
        fontSize: 11,
        fontWeight: 600,
        whiteSpace: "nowrap",
        flexShrink: 0,
      }}
    >
      {label}
    </span>
  );
}

/** Empty-state row for when data is unavailable. */
function EmptyRow({ message }: { message: string }) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 10,
        padding: "4px 0",
      }}
    >
      <div
        style={{
          width: 32,
          height: 32,
          borderRadius: 10,
          background: "var(--color-bg-2)",
          flexShrink: 0,
        }}
      />
      <p style={{ fontSize: 12, color: "var(--color-ink-3)" }}>{message}</p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

/**
 * Displays the two most recent health events:
 *   1. The latest lab panel result with the most notable flagged value.
 *   2. The most recent vitality score change derived from the trend.
 *
 * Renders empty-state rows if either data source is absent so the card
 * is always visible on the Today screen.
 */
export function RecentlyCard({ latestLab, vitality }: RecentlyCardProps) {
  // ── Lab row ────────────────────────────────────────────────────────────────
  const labRow = (() => {
    if (!latestLab) {
      return <EmptyRow message="No recent labs yet" />;
    }

    const payload = (latestLab.payload ?? {}) as Record<string, unknown>;
    const title = extractLabTitle(payload);
    const dateLabel = formatMonthYear(latestLab.recorded_at);
    const chip = extractLabChip(payload);

    return (
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 10,
        }}
      >
        <IconContainer bg="var(--color-danger-lt)">🩸</IconContainer>
        <div style={{ flex: 1, minWidth: 0 }}>
          <p
            style={{
              fontSize: 13,
              fontWeight: 600,
              color: "var(--color-ink)",
              lineHeight: 1.3,
            }}
          >
            {title}
          </p>
          {dateLabel && (
            <p
              style={{
                fontSize: 11,
                color: "var(--color-ink-3)",
                marginTop: 1,
              }}
            >
              {dateLabel}
            </p>
          )}
        </div>
        <HistoryChip label={chip.label} variant={chip.variant} />
      </div>
    );
  })();

  // ── Score row ──────────────────────────────────────────────────────────────
  const scoreRow = (() => {
    if (!vitality) {
      return <EmptyRow message="Score is steady" />;
    }

    const deltaInfo = extractScoreDelta(vitality);

    if (!deltaInfo) {
      // Current score only — no history to compare
      return (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 10,
          }}
        >
          <IconContainer bg="var(--color-accent-lt)">◆</IconContainer>
          <div style={{ flex: 1, minWidth: 0 }}>
            <p
              style={{
                fontSize: 13,
                fontWeight: 600,
                color: "var(--color-ink)",
                lineHeight: 1.3,
              }}
            >
              Vitality score {Math.round(vitality.score)}
            </p>
            <p
              style={{
                fontSize: 11,
                color: "var(--color-ink-3)",
                marginTop: 1,
              }}
            >
              Latest reading
            </p>
          </div>
          <HistoryChip label="Steady" variant="muted" />
        </div>
      );
    }

    const { delta, prev, current, prevDate } = deltaInfo;
    const direction = delta > 0 ? "up" : delta < 0 ? "down" : "flat";
    const arrow = delta > 0 ? "▲" : delta < 0 ? "▼" : "◆";
    const chipVariant: ChipVariant =
      delta > 0 ? "good" : delta < 0 ? "warn" : "muted";
    const chipLabel =
      delta !== 0 ? `${arrow} ${Math.abs(delta)} pts` : "Flat";

    const titleText =
      delta !== 0
        ? `Vitality ${direction} ${Math.abs(delta)} · ${prev} → ${current}`
        : `Vitality steady · ${current}`;

    const dateLabel = formatMonthYear(prevDate);

    return (
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 10,
        }}
      >
        <IconContainer bg="var(--color-accent-lt)">{arrow}</IconContainer>
        <div style={{ flex: 1, minWidth: 0 }}>
          <p
            style={{
              fontSize: 13,
              fontWeight: 600,
              color: "var(--color-ink)",
              lineHeight: 1.3,
            }}
          >
            {titleText}
          </p>
          {dateLabel && (
            <p
              style={{
                fontSize: 11,
                color: "var(--color-ink-3)",
                marginTop: 1,
              }}
            >
              {dateLabel}
            </p>
          )}
        </div>
        <HistoryChip label={chipLabel} variant={chipVariant} />
      </div>
    );
  })();

  return (
    <div className="card" style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      {labRow}
      {/* Divider */}
      <div
        aria-hidden="true"
        style={{
          height: 1,
          background: "var(--color-bg-2)",
          margin: "0 -4px",
        }}
      />
      {scoreRow}
    </div>
  );
}
