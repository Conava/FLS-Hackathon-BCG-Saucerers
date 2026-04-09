import * as React from "react";

const MACRO_CIRCUMFERENCE = 2 * Math.PI * 24; // ≈ 151

type Nutrient = "protein" | "fiber" | "polyphenols" | "alcohol";

const NUTRIENT_COLORS: Record<Nutrient, { fill: string; track: string }> = {
  protein: {
    fill: "var(--color-accent)",
    track: "var(--color-accent-lt)",
  },
  fiber: {
    fill: "var(--color-good)",
    track: "var(--color-good-lt)",
  },
  polyphenols: {
    fill: "var(--color-violet)",
    track: "var(--color-violet-lt)",
  },
  alcohol: {
    fill: "var(--color-warn)",
    track: "var(--color-warn-lt)",
  },
};

export interface MacroRingProps {
  /** Nutrient type — determines color scheme */
  nutrient: Nutrient;
  /** Current value */
  value: number;
  /** Target / max value — used to compute fill percentage */
  target: number;
  /** Short label shown below the ring, e.g. "Protein" */
  label: string;
}

/**
 * Small nutrition ring (62×62px) showing progress toward a nutrient target.
 */
export function MacroRing({ nutrient, value, target, label }: MacroRingProps) {
  const pct = target > 0 ? Math.min(value / target, 1) : 0;
  const offset = MACRO_CIRCUMFERENCE * (1 - pct);
  const colors = NUTRIENT_COLORS[nutrient];

  return (
    <div className="flex flex-col items-center" style={{ width: 62 }}>
      <svg
        width="60"
        height="60"
        viewBox="0 0 60 60"
        style={{ transform: "rotate(-90deg)" }}
        aria-label={`${label}: ${value} of ${target}`}
        role="img"
      >
        {/* Track */}
        <circle
          cx="30"
          cy="30"
          r="24"
          fill="none"
          stroke={colors.track}
          strokeWidth="6"
        />
        {/* Fill */}
        <circle
          cx="30"
          cy="30"
          r="24"
          fill="none"
          stroke={colors.fill}
          strokeWidth="6"
          strokeLinecap="round"
          strokeDasharray={MACRO_CIRCUMFERENCE}
          strokeDashoffset={offset}
        />
      </svg>

      <span
        className="font-bold tabular-nums"
        style={{
          fontSize: 12,
          color: "var(--color-ink)",
          marginTop: 4,
        }}
      >
        {value}
      </span>
      <span
        className="uppercase"
        style={{
          fontSize: 10,
          fontWeight: 600,
          color: "var(--color-ink-3)",
          letterSpacing: "0.04em",
        }}
      >
        {label}
      </span>
    </div>
  );
}
