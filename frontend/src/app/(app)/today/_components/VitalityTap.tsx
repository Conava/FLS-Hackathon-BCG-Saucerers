"use client";

import * as React from "react";
import { VitalityRing } from "@/components/design";
import { SignalsSheet } from "./SignalsSheet";
import { COPY } from "@/lib/copy/copy";
import type { InsightOut } from "@/lib/api/schemas";

export interface VitalityTapProps {
  /** Vitality score 0–100 */
  score: number;
  /** Change from previous period */
  delta: number;
  /** Insights list for the signals sheet (may be empty) */
  insights: InsightOut[];
}

/**
 * Client wrapper around VitalityRing that owns the SignalsSheet open state.
 * Tapping the ring opens a bottom sheet with the four longevity dimensions.
 */
export function VitalityTap({ score, delta, insights }: VitalityTapProps) {
  const [sheetOpen, setSheetOpen] = React.useState(false);

  return (
    <>
      {/* Tappable wrapper — button role for a11y */}
      <button
        type="button"
        aria-label="View signals"
        onClick={() => setSheetOpen(true)}
        className="block rounded-full focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
        style={{ background: "transparent", border: "none", padding: 0, cursor: "pointer" }}
      >
        <VitalityRing
          score={score}
          delta={delta}
          label={COPY.today.scoreLabel}
        />
      </button>

      <SignalsSheet
        open={sheetOpen}
        onClose={() => setSheetOpen(false)}
        insights={insights}
      />
    </>
  );
}
