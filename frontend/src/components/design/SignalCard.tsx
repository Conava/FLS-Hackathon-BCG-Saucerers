"use client";

import * as React from "react";

type TrendDirection = "up" | "down" | "neutral";

export interface SignalCardProps {
  /** Longevity dimension name, e.g. "Sleep" */
  label: string;
  /** Numeric score or value to display */
  value: string | number;
  /** Optional sub-text, colored by status */
  subText?: string;
  /** Status determines sub-text color and icon box tint */
  status?: "good" | "warn" | "neutral";
  /** Trend arrow direction */
  trend?: TrendDirection;
  /** Icon element (14×14 SVG or emoji) */
  icon?: React.ReactNode;
  /** Called when the card is tapped */
  onClick?: () => void;
}

const TREND_ARROW: Record<TrendDirection, { path: string; color: string }> = {
  up: { path: "M12 19V5M5 12l7-7 7 7", color: "var(--color-good)" },
  down: { path: "M12 5v14M5 12l7 7 7-7", color: "var(--color-danger)" },
  neutral: { path: "M5 12h14", color: "var(--color-ink-3)" },
};

/**
 * Small card for Insights longevity dimensions showing icon + label + score + trend.
 */
export function SignalCard({
  label,
  value,
  subText,
  status = "neutral",
  trend,
  icon,
  onClick,
}: SignalCardProps) {
  const iconBoxStyle =
    status === "warn"
      ? {
          background: "var(--color-warn-lt)",
          color: "var(--color-warn)",
        }
      : {
          background: "var(--color-accent-lt)",
          color: "var(--color-accent)",
        };

  const subTextColor =
    status === "warn"
      ? "var(--color-warn)"
      : status === "good"
      ? "var(--color-good)"
      : "var(--color-ink-3)";

  return (
    <article
      className="bg-surface cursor-pointer transition-transform hover:-translate-y-0.5"
      style={{
        border: "1px solid var(--color-border)",
        borderRadius: 14,
        padding: 12,
      }}
      onClick={onClick}
      role={onClick ? "button" : undefined}
      tabIndex={onClick ? 0 : undefined}
      onKeyDown={
        onClick
          ? (e) => {
              if (e.key === "Enter" || e.key === " ") onClick();
            }
          : undefined
      }
    >
      {/* Icon box */}
      <div
        className="flex items-center justify-center rounded-lg mb-2"
        style={{ width: 28, height: 28, borderRadius: 8, ...iconBoxStyle }}
        aria-hidden="true"
      >
        {icon}
      </div>

      {/* Label */}
      <p
        className="uppercase"
        style={{
          fontSize: 11,
          fontWeight: 600,
          color: "var(--color-ink-3)",
          letterSpacing: "0.04em",
        }}
      >
        {label}
      </p>

      {/* Value row */}
      <div className="flex items-center gap-1 mt-0.5">
        <span
          className="t-stat-md tabular-nums"
          style={{ color: "var(--color-ink)" }}
        >
          {value}
        </span>
        {trend && (
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke={TREND_ARROW[trend].color}
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <path d={TREND_ARROW[trend].path} />
          </svg>
        )}
      </div>

      {/* Sub text */}
      {subText && (
        <p style={{ fontSize: 11, fontWeight: 600, color: subTextColor, marginTop: 2 }}>
          {subText}
        </p>
      )}
    </article>
  );
}
