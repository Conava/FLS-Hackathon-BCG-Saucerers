"use client";

import * as React from "react";
import { BottomSheet } from "@/components/design/BottomSheet";
import * as apiClient from "@/lib/api/client";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface QuickLogWaterSheetProps {
  /** Whether the sheet is visible. */
  open: boolean;
  /** Called when the sheet requests a visibility change. */
  onOpenChange: (open: boolean) => void;
  /** Optional callback invoked after a successful log submission. */
  onSubmitted?: () => void;
}

/** Quick-add preset amounts in millilitres. */
const QUICK_ADD_AMOUNTS = [250, 500, 750] as const;

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/**
 * Bottom-sheet form for quickly logging water intake.
 *
 * Fields:
 * - Quick-add row: +250 ml / +500 ml / +750 ml buttons — tapping any of them
 *   sets the custom input to that value.
 * - Custom ml input (number, step 50, min 50, max 3000)
 *
 * Submit calls `createDailyLog({ date: today, water_ml: value })`.
 * On success: calls `onSubmitted`, then closes the sheet via `onOpenChange(false)`.
 * On error: displays an inline error message and keeps the sheet open.
 */
export function QuickLogWaterSheet({
  open,
  onOpenChange,
  onSubmitted,
}: QuickLogWaterSheetProps) {
  const [waterMl, setWaterMl] = React.useState<number>(500);
  const [saving, setSaving] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  /** Reset transient state when the sheet opens freshly. */
  React.useEffect(() => {
    if (open) {
      setWaterMl(500);
      setSaving(false);
      setError(null);
    }
  }, [open]);

  function handleClose() {
    onOpenChange(false);
  }

  async function handleSave() {
    if (saving) return;
    setSaving(true);
    setError(null);

    // ISO date string for today in local time
    const today = new Date().toISOString().slice(0, 10);

    try {
      await apiClient.createDailyLog({
        date: today,
        water_ml: waterMl,
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
    <BottomSheet open={open} onClose={handleClose} title="Log water">
      <div className="mt-5 flex flex-col gap-6">
        {/* Quick-add buttons row */}
        <div className="flex flex-col gap-2">
          <span
            className="t-label text-ink-2"
            style={{ fontSize: "0.875rem", fontWeight: 500 }}
          >
            Quick add
          </span>
          <div
            className="flex gap-3"
            role="group"
            aria-label="Quick-add water presets"
          >
            {QUICK_ADD_AMOUNTS.map((amount) => (
              <button
                key={amount}
                type="button"
                aria-label={`+${amount} ml`}
                onClick={() => setWaterMl(amount)}
                className="flex-1 rounded-xl py-3 t-label font-semibold transition-colors"
                style={{
                  background:
                    waterMl === amount
                      ? "var(--color-accent)"
                      : "var(--color-surface)",
                  color: waterMl === amount ? "#fff" : "var(--color-ink)",
                  border:
                    waterMl === amount
                      ? "2px solid var(--color-accent)"
                      : "2px solid var(--color-border-2)",
                  cursor: "pointer",
                  fontSize: "0.875rem",
                }}
              >
                +{amount} ml
              </button>
            ))}
          </div>
        </div>

        {/* Custom ml input */}
        <div className="flex flex-col gap-2">
          <label
            htmlFor="water-ml-input"
            className="t-label text-ink-2"
            style={{ fontSize: "0.875rem", fontWeight: 500 }}
          >
            Amount (ml)
          </label>
          <input
            id="water-ml-input"
            type="number"
            step={50}
            min={50}
            max={3000}
            value={waterMl}
            onChange={(e) => {
              const parsed = parseInt(e.target.value, 10);
              if (!isNaN(parsed)) setWaterMl(parsed);
            }}
            className="card rounded-xl px-4 py-3 text-ink text-base w-full"
            style={{
              background: "var(--color-surface)",
              border: "1px solid var(--color-border-2)",
              outline: "none",
            }}
            aria-label="Amount in millilitres"
          />
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
          onClick={() => void handleSave()}
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
