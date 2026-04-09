"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { WeeklyCheckInSheet } from "@/components/trackers/WeeklyCheckInSheet";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface WeeklyCheckInCardProps {
  /**
   * Days since the last weekly check-in submission.
   * null means no prior submission found.
   */
  daysSinceLastCheckIn: number | null;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Build the subtitle text shown under the card label.
 *
 * - null → "Not done this week"
 * - 0 → "Completed today"
 * - 1 → "Last check-in 1 day ago"
 * - N → "Last check-in N days ago"
 */
function buildSubtitle(days: number | null): string {
  if (days === null) return "Not done this week";
  if (days === 0) return "Completed today";
  if (days === 1) return "Last check-in 1 day ago";
  return `Last check-in ${days} days ago`;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/**
 * Interactive card for the weekly 30-second check-in.
 *
 * Displays when the last check-in occurred and offers a "Start" button that
 * opens the WeeklyCheckInSheet. On success it refreshes the page so the
 * server component re-fetches the survey history.
 */
export function WeeklyCheckInCard({ daysSinceLastCheckIn }: WeeklyCheckInCardProps) {
  const router = useRouter();
  const [sheetOpen, setSheetOpen] = React.useState(false);

  function handleSubmitted() {
    router.refresh();
    setSheetOpen(false);
  }

  const subtitle = buildSubtitle(daysSinceLastCheckIn);

  return (
    <>
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
              {subtitle}
            </p>
          </div>
          <button
            type="button"
            aria-label="Start weekly check-in"
            onClick={() => setSheetOpen(true)}
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

      <WeeklyCheckInSheet
        open={sheetOpen}
        onOpenChange={setSheetOpen}
        onSubmitted={handleSubmitted}
      />
    </>
  );
}
