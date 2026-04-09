"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { QuickLogMealSheet } from "@/components/trackers/QuickLogMealSheet";
import { QuickLogSleepSheet } from "@/components/trackers/QuickLogSleepSheet";
import { QuickLogWorkoutSheet } from "@/components/trackers/QuickLogWorkoutSheet";
import { QuickLogWaterSheet } from "@/components/trackers/QuickLogWaterSheet";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type SheetKey = "meal" | "sleep" | "workout" | "water";

interface QuickLogItem {
  emoji: string;
  label: string;
  sheet: SheetKey;
}

const ITEMS: QuickLogItem[] = [
  { emoji: "🍽️", label: "Meal", sheet: "meal" },
  { emoji: "😴", label: "Sleep", sheet: "sleep" },
  { emoji: "🏃", label: "Workout", sheet: "workout" },
  { emoji: "💧", label: "Water", sheet: "water" },
];

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/**
 * 4-column quick-log grid for the Today screen.
 *
 * Each tile opens its corresponding bottom sheet:
 * - Meal → QuickLogMealSheet (with internal "Prefer the camera?" link to /meal-log)
 * - Sleep → QuickLogSleepSheet
 * - Workout → QuickLogWorkoutSheet
 * - Water → QuickLogWaterSheet
 *
 * On successful submission the page is refreshed via router.refresh().
 */
export function QuickLogGrid() {
  const router = useRouter();
  const [openSheet, setOpenSheet] = React.useState<null | SheetKey>(null);

  function handleSubmitted() {
    router.refresh();
    setOpenSheet(null);
  }

  return (
    <>
      {/* ── 4-column grid ───────────────────────────────────────────────── */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(4, 1fr)",
          gap: 8,
        }}
      >
        {ITEMS.map(({ emoji, label, sheet }) => (
          <button
            key={label}
            type="button"
            aria-label={label}
            onClick={() => setOpenSheet(sheet)}
            className="card"
            style={{
              padding: "12px 6px",
              textAlign: "center",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              cursor: "pointer",
              border: "1px solid var(--color-border)",
              background: "var(--color-surface)",
              boxShadow: "none",
              width: "100%",
            }}
          >
            <span style={{ fontSize: 20 }} aria-hidden="true">
              {emoji}
            </span>
            <span
              style={{
                fontSize: 10.5,
                fontWeight: 600,
                marginTop: 4,
                color: "var(--color-ink)",
              }}
            >
              {label}
            </span>
          </button>
        ))}
      </div>

      {/* ── Sheets ─────────────────────────────────────────────────────── */}
      <QuickLogMealSheet
        open={openSheet === "meal"}
        onOpenChange={(v) => setOpenSheet(v ? "meal" : null)}
        onSubmitted={handleSubmitted}
      />
      <QuickLogSleepSheet
        open={openSheet === "sleep"}
        onOpenChange={(v) => setOpenSheet(v ? "sleep" : null)}
        onSubmitted={handleSubmitted}
      />
      <QuickLogWorkoutSheet
        open={openSheet === "workout"}
        onOpenChange={(v) => setOpenSheet(v ? "workout" : null)}
        onSubmitted={handleSubmitted}
      />
      <QuickLogWaterSheet
        open={openSheet === "water"}
        onOpenChange={(v) => setOpenSheet(v ? "water" : null)}
        onSubmitted={handleSubmitted}
      />
    </>
  );
}
