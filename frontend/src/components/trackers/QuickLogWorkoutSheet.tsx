"use client";

import * as React from "react";
import { BottomSheet } from "@/components/design/BottomSheet";
import { createDailyLog } from "@/lib/api/client";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type WorkoutType = "walk" | "run" | "bike" | "strength" | "yoga" | "other";
type WorkoutIntensity = "low" | "medium" | "high";

export interface QuickLogWorkoutSheetProps {
  /** Whether the sheet is visible. */
  open: boolean;
  /** Called when the sheet requests open/close state change. */
  onOpenChange: (open: boolean) => void;
  /** Called after a successful log submission. */
  onSubmitted?: () => void;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const WORKOUT_TILES: { type: WorkoutType; emoji: string; label: string }[] = [
  { type: "walk", emoji: "🚶", label: "Walk" },
  { type: "run", emoji: "🏃", label: "Run" },
  { type: "bike", emoji: "🚴", label: "Bike" },
  { type: "strength", emoji: "💪", label: "Strength" },
  { type: "yoga", emoji: "🧘", label: "Yoga" },
  { type: "other", emoji: "⚡", label: "Other" },
];

const INTENSITY_OPTIONS: { value: WorkoutIntensity; label: string }[] = [
  { value: "low", label: "Low" },
  { value: "medium", label: "Medium" },
  { value: "high", label: "High" },
];

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/**
 * Bottom sheet form for quickly logging a workout session.
 *
 * Lets the user pick:
 * - Workout type (6 tappable tiles)
 * - Duration in minutes (number input, step 5, 5–240, default 30)
 * - Intensity (Low / Medium / High pill buttons)
 *
 * On submit calls `createDailyLog` with the selected values and today's date.
 */
export function QuickLogWorkoutSheet({
  open,
  onOpenChange,
  onSubmitted,
}: QuickLogWorkoutSheetProps) {
  const [workoutType, setWorkoutType] = React.useState<WorkoutType>("walk");
  const [duration, setDuration] = React.useState<number>(30);
  const [intensity, setIntensity] = React.useState<WorkoutIntensity>("medium");
  const [submitting, setSubmitting] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  function handleClose() {
    onOpenChange(false);
  }

  function resetForm() {
    setWorkoutType("walk");
    setDuration(30);
    setIntensity("medium");
    setError(null);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);

    try {
      const today = new Date().toISOString().split("T")[0] ?? "";
      await createDailyLog({
        date: today,
        workout_minutes: duration,
        workout_type: workoutType,
        workout_intensity: intensity,
      });
      onSubmitted?.();
      resetForm();
      onOpenChange(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to log workout");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <BottomSheet open={open} onClose={handleClose} title="Log workout">
      <form onSubmit={handleSubmit} style={{ marginTop: 20 }}>
        {/* Workout type tiles */}
        <fieldset style={{ border: "none", padding: 0, margin: "0 0 20px" }}>
          <legend
            className="t-support text-ink-3"
            style={{ marginBottom: 10, display: "block" }}
          >
            Type
          </legend>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(3, 1fr)",
              gap: 8,
            }}
          >
            {WORKOUT_TILES.map(({ type, emoji, label }) => {
              const selected = workoutType === type;
              return (
                <button
                  key={type}
                  type="button"
                  aria-pressed={selected}
                  onClick={() => setWorkoutType(type)}
                  className={
                    selected
                      ? "bg-accent-lt border border-accent text-accent"
                      : "bg-bg-2 border border-border text-ink-2"
                  }
                  style={{
                    borderRadius: 12,
                    padding: "12px 8px",
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "center",
                    gap: 4,
                    cursor: "pointer",
                    transition: "all 0.15s",
                  }}
                >
                  <span style={{ fontSize: 22 }} aria-hidden="true">
                    {emoji}
                  </span>
                  <span className="t-support" style={{ fontSize: 12 }}>
                    {label}
                  </span>
                </button>
              );
            })}
          </div>
        </fieldset>

        {/* Duration input */}
        <div style={{ marginBottom: 20 }}>
          <label
            htmlFor="workout-duration"
            className="t-support text-ink-3"
            style={{ display: "block", marginBottom: 8 }}
          >
            Duration (min)
          </label>
          <input
            id="workout-duration"
            type="number"
            min={5}
            max={240}
            step={5}
            value={duration}
            onChange={(e) => {
              const v = parseInt(e.target.value, 10);
              if (!isNaN(v)) setDuration(v);
            }}
            className="bg-bg-2 border border-border text-ink rounded-xl"
            style={{
              width: "100%",
              padding: "12px 14px",
              fontSize: 16,
              outline: "none",
            }}
          />
        </div>

        {/* Intensity pills */}
        <fieldset style={{ border: "none", padding: 0, margin: "0 0 24px" }}>
          <legend
            className="t-support text-ink-3"
            style={{ marginBottom: 10, display: "block" }}
          >
            Intensity
          </legend>
          <div style={{ display: "flex", gap: 8 }}>
            {INTENSITY_OPTIONS.map(({ value, label }) => {
              const selected = intensity === value;
              return (
                <button
                  key={value}
                  type="button"
                  aria-pressed={selected}
                  onClick={() => setIntensity(value)}
                  className={
                    selected
                      ? "bg-accent text-surface"
                      : "bg-bg-2 border border-border text-ink-2"
                  }
                  style={{
                    flex: 1,
                    borderRadius: 999,
                    padding: "10px 0",
                    fontSize: 13,
                    fontWeight: 600,
                    cursor: "pointer",
                    transition: "all 0.15s",
                    border: selected ? "none" : undefined,
                  }}
                >
                  {label}
                </button>
              );
            })}
          </div>
        </fieldset>

        {/* Error message */}
        {error && (
          <p
            role="alert"
            className="text-danger t-support"
            style={{ marginBottom: 12 }}
          >
            {error}
          </p>
        )}

        {/* Submit button */}
        <button
          type="submit"
          disabled={submitting}
          className="bg-accent text-surface w-full"
          style={{
            borderRadius: 14,
            padding: "14px 0",
            fontSize: 15,
            fontWeight: 700,
            opacity: submitting ? 0.6 : 1,
            cursor: submitting ? "not-allowed" : "pointer",
            border: "none",
            transition: "opacity 0.15s",
          }}
          aria-label="Log workout"
        >
          {submitting ? "Saving…" : "Log workout"}
        </button>
      </form>
    </BottomSheet>
  );
}
