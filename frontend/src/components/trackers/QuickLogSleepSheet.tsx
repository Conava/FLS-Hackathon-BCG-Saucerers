"use client";

import * as React from "react";
import { BottomSheet } from "@/components/design/BottomSheet";
import * as apiClient from "@/lib/api/client";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface QuickLogSleepSheetProps {
  /** Whether the sheet is visible. */
  open: boolean;
  /** Called when the sheet requests a visibility change. */
  onOpenChange: (open: boolean) => void;
  /** Optional callback invoked after a successful log submission. */
  onSubmitted?: () => void;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/**
 * Bottom-sheet form for quickly logging sleep data.
 *
 * Fields:
 * - Sleep hours (number input, step 0.25, min 0, max 14, default 7.5)
 * - Sleep quality 1–5 (tappable circular buttons)
 *
 * On success: calls `onSubmitted`, then closes the sheet.
 * On error: displays an inline error message and keeps the sheet open.
 */
export function QuickLogSleepSheet({
  open,
  onOpenChange,
  onSubmitted,
}: QuickLogSleepSheetProps) {
  const [sleepHours, setSleepHours] = React.useState<number>(7.5);
  const [sleepQuality, setSleepQuality] = React.useState<number>(3);
  const [saving, setSaving] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  /** Reset transient state when the sheet opens freshly. */
  React.useEffect(() => {
    if (open) {
      setSleepHours(7.5);
      setSleepQuality(3);
      setSaving(false);
      setError(null);
    }
  }, [open]);

  function handleClose() {
    onOpenChange(false);
  }

  async function handleSave() {
    setSaving(true);
    setError(null);

    // ISO date string for today in local time
    const today = new Date().toISOString().slice(0, 10);

    try {
      await apiClient.createDailyLog({
        date: today,
        sleep_hours: sleepHours,
        sleep_quality: sleepQuality,
      });
      onSubmitted?.();
      onOpenChange(false);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Something went wrong. Please try again.";
      setError(message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <BottomSheet open={open} onClose={handleClose} title="Log sleep">
      <div className="mt-5 flex flex-col gap-6">
        {/* Sleep hours field */}
        <div className="flex flex-col gap-2">
          <label
            htmlFor="sleep-hours-input"
            className="t-label text-ink-2"
            style={{ fontSize: "0.875rem", fontWeight: 500 }}
          >
            Sleep hours
          </label>
          <input
            id="sleep-hours-input"
            type="number"
            step={0.25}
            min={0}
            max={14}
            value={sleepHours}
            onChange={(e) => setSleepHours(parseFloat(e.target.value) || 0)}
            className="card rounded-xl px-4 py-3 text-ink text-base w-full"
            style={{
              background: "var(--color-surface)",
              border: "1px solid var(--color-border-2)",
              outline: "none",
            }}
            aria-label="Sleep hours"
          />
        </div>

        {/* Sleep quality field */}
        <div className="flex flex-col gap-3">
          <span
            className="t-label text-ink-2"
            style={{ fontSize: "0.875rem", fontWeight: 500 }}
          >
            Sleep quality
          </span>
          <div
            className="flex gap-3"
            role="group"
            aria-label="Sleep quality 1 to 5"
          >
            {([1, 2, 3, 4, 5] as const).map((level) => {
              const selected = sleepQuality === level;
              return (
                <button
                  key={level}
                  type="button"
                  aria-label={String(level)}
                  aria-pressed={selected}
                  data-selected={selected ? "true" : "false"}
                  onClick={() => setSleepQuality(level)}
                  className="flex items-center justify-center rounded-full t-label font-semibold transition-colors"
                  style={{
                    width: 44,
                    height: 44,
                    background: selected
                      ? "var(--color-accent)"
                      : "var(--color-surface)",
                    color: selected ? "#fff" : "var(--color-ink)",
                    border: selected
                      ? "2px solid var(--color-accent)"
                      : "2px solid var(--color-border-2)",
                    cursor: "pointer",
                  }}
                >
                  {level}
                </button>
              );
            })}
          </div>
        </div>

        {/* Inline error */}
        {error && (
          <p
            role="alert"
            className="t-body"
            style={{
              color: "var(--color-error, #e53e3e)",
              fontSize: "0.875rem",
            }}
          >
            {error}
          </p>
        )}
      </div>

      {/* Action row */}
      <div className="mt-7 flex gap-3">
        <button
          type="button"
          onClick={handleClose}
          disabled={saving}
          className="flex-1 rounded-xl py-3 t-label font-semibold"
          style={{
            background: "var(--color-surface)",
            border: "1px solid var(--color-border-2)",
            color: "var(--color-ink-2)",
            cursor: saving ? "not-allowed" : "pointer",
          }}
          aria-label="Cancel"
        >
          Cancel
        </button>
        <button
          type="button"
          onClick={handleSave}
          disabled={saving}
          className="flex-1 rounded-xl py-3 t-label font-semibold"
          style={{
            background: "var(--color-accent)",
            color: "#fff",
            border: "none",
            cursor: saving ? "not-allowed" : "pointer",
            opacity: saving ? 0.7 : 1,
          }}
          aria-label="Save"
        >
          {saving ? "Saving…" : "Save"}
        </button>
      </div>
    </BottomSheet>
  );
}
