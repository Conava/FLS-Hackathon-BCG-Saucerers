"use client";

import * as React from "react";

const CIRCUMFERENCE = 2 * Math.PI * 78; // ≈ 490

function useReducedMotion(): boolean {
  const [reduced, setReduced] = React.useState(false);

  React.useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReduced(mq.matches);
    const handler = (e: MediaQueryListEvent) => setReduced(e.matches);
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);

  return reduced;
}

export interface VitalityRingProps {
  /** Vitality score 0–100 */
  score: number;
  /** Change from previous period, positive = improvement */
  delta: number;
  /** Label shown below the number, e.g. "Vitality Score" */
  label: string;
}

/**
 * Hero animated SVG ring showing the patient's vitality score.
 * Respects `prefers-reduced-motion` — skips stroke animation when enabled.
 */
export function VitalityRing({ score, delta, label }: VitalityRingProps) {
  const reduced = useReducedMotion();
  const [offset, setOffset] = React.useState(CIRCUMFERENCE);

  React.useEffect(() => {
    const target = CIRCUMFERENCE * (1 - score / 100);
    if (reduced) {
      setOffset(target);
    } else {
      // Trigger after a paint tick so CSS transition fires
      const id = requestAnimationFrame(() => setOffset(target));
      return () => cancelAnimationFrame(id);
    }
  }, [score, reduced]);

  const deltaColor =
    delta > 0 ? "text-good" : delta < 0 ? "text-danger" : "text-ink-3";
  const deltaArrow = delta > 0 ? "▲" : delta < 0 ? "▼" : "";
  const deltaAbs = Math.abs(delta);

  return (
    <div
      className="relative"
      style={{ width: 168, height: 168 }}
      aria-label={`Vitality score ${Math.round(score)}`}
      role="img"
    >
      <svg
        width="100%"
        height="100%"
        style={{ transform: "rotate(-90deg)" }}
        aria-hidden="true"
      >
        {/* Track */}
        <circle
          cx="84"
          cy="84"
          r="78"
          fill="none"
          stroke="var(--color-bg-2)"
          strokeWidth="12"
        />
        {/* Fill */}
        <circle
          cx="84"
          cy="84"
          r="78"
          fill="none"
          stroke="var(--color-accent)"
          strokeWidth="12"
          strokeLinecap="round"
          strokeDasharray={CIRCUMFERENCE}
          strokeDashoffset={offset}
          style={
            reduced
              ? undefined
              : { transition: "stroke-dashoffset 1s cubic-bezier(.4,0,.2,1)" }
          }
        />
      </svg>

      {/* Center overlay */}
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="t-ring-num text-ink">{Math.round(score)}</span>
        <span
          className="t-micro text-ink-3"
          style={{ marginTop: 4 }}
        >
          {label}
        </span>
        {delta !== 0 && (
          <span
            className={`t-micro font-bold ${deltaColor}`}
            style={{ marginTop: 6, display: "inline-flex", alignItems: "center", gap: 3 }}
          >
            {deltaArrow} {deltaAbs} vs last week
          </span>
        )}
      </div>
    </div>
  );
}
