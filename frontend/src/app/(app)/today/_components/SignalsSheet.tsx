"use client";

import * as React from "react";
import { BottomSheet } from "@/components/design";
import { SignalCard } from "@/components/design";
import { EmptyState } from "@/components/design";
import type { InsightOut } from "@/lib/api/schemas";

export interface SignalsSheetProps {
  /** Whether the sheet is visible. */
  open: boolean;
  /** Called when the sheet should close. */
  onClose: () => void;
  /** Insight objects from the /insights endpoint. */
  insights: InsightOut[];
}

/** Map insight kind to a human-readable label. */
function kindLabel(kind: string): string {
  const MAP: Record<string, string> = {
    sleep: "Sleep & Recovery",
    cardiovascular: "Cardio Fitness",
    metabolic: "Metabolic Health",
    lifestyle: "Lifestyle & Behaviour",
    nutrition: "Nutrition",
    stress: "Stress & Recovery",
    mental_wellness: "Mental Wellness",
    activity: "Activity",
  };
  return MAP[kind] ?? kind.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

/** Map severity to SignalCard status. */
function severityToStatus(
  severity: InsightOut["severity"]
): "good" | "warn" | "neutral" {
  if (severity === "low") return "good";
  if (severity === "high") return "warn";
  return "neutral";
}

/** Small icon per insight kind. */
function KindIcon({ kind }: { kind: string }) {
  if (kind === "sleep" || kind === "stress") {
    return (
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
      </svg>
    );
  }
  if (kind === "cardiovascular") {
    return (
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" />
      </svg>
    );
  }
  if (kind === "metabolic" || kind === "nutrition") {
    return (
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <circle cx="12" cy="12" r="10" />
        <path d="M12 8v4l3 3" />
      </svg>
    );
  }
  // Default: activity / lifestyle
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
    </svg>
  );
}

/**
 * BottomSheet showing 4 longevity dimension SignalCards.
 * Opened by tapping the VitalityRing on the Today screen.
 *
 * AI disclosure: this is a data drill-down, not AI chat, so no banner is needed.
 */
export function SignalsSheet({ open, onClose, insights }: SignalsSheetProps) {
  return (
    <BottomSheet open={open} onClose={onClose} title="Longevity Signals">
      {insights.length === 0 ? (
        <EmptyState
          heading="No signals available"
          subtext="Sync more data to unlock your longevity signal breakdown."
          icon={
            <svg
              width="24"
              height="24"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
            </svg>
          }
        />
      ) : (
        <div
          className="grid grid-cols-2 gap-3"
          style={{ marginTop: 16 }}
          aria-label="Longevity dimension signals"
        >
          {insights.map((insight) => (
            <SignalCard
              key={insight.kind}
              label={kindLabel(insight.kind)}
              value={insight.severity}
              subText={insight.message}
              status={severityToStatus(insight.severity)}
              icon={<KindIcon kind={insight.kind} />}
            />
          ))}
        </div>
      )}
    </BottomSheet>
  );
}
