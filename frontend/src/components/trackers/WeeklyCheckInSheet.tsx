"use client";

/**
 * WeeklyCheckInSheet — BottomSheet for the 30-second weekly wellness check-in.
 *
 * Three 1–5 segmented questions (energy, sleep quality, mood). On submit,
 * calls `submitWeeklyCheckIn` and fires `onSubmitted` on success.
 *
 * AI disclosure: this form does not involve AI — no banner required.
 */

import * as React from "react";
import { BottomSheet } from "@/components/design/BottomSheet";
import { submitWeeklyCheckIn } from "@/lib/api/client";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface WeeklyCheckInSheetProps {
  /** Whether the sheet is visible. */
  open: boolean;
  /** Called when the sheet requests open/close state change. */
  onOpenChange: (open: boolean) => void;
  /** Optional callback after a successful submission. */
  onSubmitted?: () => void;
}

// ---------------------------------------------------------------------------
// Sub-component: 1-5 scale row
// ---------------------------------------------------------------------------

interface ScaleRowProps {
  /** Question label shown above the buttons. */
  label: string;
  /** Low-end hint (e.g. "very low"). */
  lowHint: string;
  /** High-end hint (e.g. "very high"). */
  highHint: string;
  /** Currently selected value (1–5) or null. */
  value: number | null;
  /** Called when a button is tapped. */
  onChange: (v: number) => void;
}

/**
 * Single question row with a label and 5 circular tap-targets (1–5).
 */
function ScaleRow({ label, lowHint, highHint, value, onChange }: ScaleRowProps) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      {/* Question label */}
      <p
        className="t-body-strong text-ink"
        style={{ margin: 0 }}
      >
        {label}
      </p>

      {/* Scale buttons */}
      <div
        style={{
          display: "flex",
          gap: 8,
          alignItems: "center",
        }}
        role="group"
        aria-label={label}
      >
        {[1, 2, 3, 4, 5].map((n) => {
          const selected = value === n;
          return (
            <button
              key={n}
              type="button"
              aria-label={String(n)}
              data-selected={selected ? "true" : "false"}
              onClick={() => onChange(n)}
              style={{
                width: 44,
                height: 44,
                borderRadius: "50%",
                border: selected
                  ? "2px solid var(--color-accent)"
                  : "1.5px solid var(--color-border)",
                background: selected
                  ? "var(--color-accent)"
                  : "var(--color-surface)",
                color: selected ? "#fff" : "var(--color-ink)",
                fontSize: 15,
                fontWeight: 600,
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                flexShrink: 0,
                transition: "background 150ms, border-color 150ms, color 150ms",
              }}
            >
              {n}
            </button>
          );
        })}
      </div>

      {/* Hint labels */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
        }}
      >
        <span className="t-support text-ink-3">{lowHint}</span>
        <span className="t-support text-ink-3">{highHint}</span>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

/**
 * 30-second weekly check-in sheet with three 1-5 wellness scale questions.
 *
 * Submits via `submitWeeklyCheckIn` (POST /api/proxy/survey with kind=weekly).
 * Calls `onSubmitted` and closes on success; shows inline error on failure.
 */
export function WeeklyCheckInSheet({
  open,
  onOpenChange,
  onSubmitted,
}: WeeklyCheckInSheetProps) {
  const [energy, setEnergy] = React.useState<number | null>(null);
  const [sleep, setSleep] = React.useState<number | null>(null);
  const [mood, setMood] = React.useState<number | null>(null);
  const [submitting, setSubmitting] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  /** Reset local state when the sheet is closed. */
  const reset = () => {
    setEnergy(null);
    setSleep(null);
    setMood(null);
    setSubmitting(false);
    setError(null);
  };

  const handleClose = () => {
    reset();
    onOpenChange(false);
  };

  const handleSubmit = async () => {
    if (submitting) return;

    // All three questions are required
    if (energy === null || sleep === null || mood === null) {
      setError("Please rate all three questions before saving.");
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      await submitWeeklyCheckIn({ energy, sleep, mood });
      reset();
      onSubmitted?.();
      onOpenChange(false);
    } catch (err) {
      const msg =
        err instanceof Error ? err.message : "Something went wrong. Please try again.";
      setError(msg);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <BottomSheet
      open={open}
      onClose={handleClose}
      title="30-second check-in"
    >
      <div style={{ display: "flex", flexDirection: "column", gap: 24, marginTop: 4 }}>
        {/* Subtitle */}
        <p className="t-body text-ink-3" style={{ margin: 0 }}>
          Quick pulse on how your week felt.
        </p>

        {/* Question 1: Energy */}
        <ScaleRow
          label="Energy this week"
          lowHint="Very low"
          highHint="Very high"
          value={energy}
          onChange={setEnergy}
        />

        {/* Question 2: Sleep quality */}
        <ScaleRow
          label="Sleep quality"
          lowHint="Poor"
          highHint="Excellent"
          value={sleep}
          onChange={setSleep}
        />

        {/* Question 3: Mood */}
        <ScaleRow
          label="Mood"
          lowHint="Low"
          highHint="Great"
          value={mood}
          onChange={setMood}
        />

        {/* Inline error */}
        {error && (
          <p
            role="alert"
            className="t-support"
            style={{ color: "var(--color-error, #d32f2f)", margin: 0 }}
          >
            {error}
          </p>
        )}

        {/* Actions */}
        <div style={{ display: "flex", gap: 12 }}>
          <button
            type="button"
            onClick={handleClose}
            aria-label="Cancel"
            style={{
              flex: 1,
              padding: "12px 16px",
              borderRadius: 14,
              border: "1px solid var(--color-border)",
              background: "transparent",
              color: "var(--color-ink)",
              fontSize: 15,
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={() => void handleSubmit()}
            disabled={submitting}
            aria-label={submitting ? "Saving…" : "Save"}
            style={{
              flex: 2,
              padding: "12px 16px",
              borderRadius: 14,
              border: "none",
              background: submitting
                ? "var(--color-bg-2)"
                : "var(--color-accent)",
              color: submitting ? "var(--color-ink-3)" : "#fff",
              fontSize: 15,
              fontWeight: 600,
              cursor: submitting ? "default" : "pointer",
            }}
          >
            {submitting ? "Saving…" : "Save"}
          </button>
        </div>
      </div>
    </BottomSheet>
  );
}
