import * as React from "react";

export interface StepperProgressProps {
  /** Total number of steps */
  total: number;
  /** Current step index (1-based) */
  current: number;
}

/**
 * Onboarding step progress bar.
 * Thin accent-colored bar that transitions width as the user advances.
 */
export function StepperProgress({ total, current }: StepperProgressProps) {
  const pct = Math.round((Math.max(0, current - 1) / Math.max(1, total - 1)) * 100);

  return (
    <div
      className="w-full rounded-full overflow-hidden"
      style={{ height: 4, background: "var(--color-bg-2)" }}
      role="progressbar"
      aria-valuenow={current}
      aria-valuemin={1}
      aria-valuemax={total}
      aria-label={`Step ${current} of ${total}`}
    >
      <span
        className="block h-full rounded-full"
        style={{
          width: `${pct}%`,
          background: "var(--color-accent)",
          transition: "width 0.4s ease",
        }}
      />
    </div>
  );
}
