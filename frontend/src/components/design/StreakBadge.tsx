import * as React from "react";

export interface StreakBadgeProps {
  /** Number of consecutive days in the streak */
  days: number;
}

/**
 * Pill-shaped gamification streak badge with a flame icon and day count.
 */
export function StreakBadge({ days }: StreakBadgeProps) {
  return (
    <span
      className="inline-flex items-center gap-1.5 font-bold"
      style={{
        background: "linear-gradient(135deg, #FDF3DC 0%, #F8E6B3 100%)",
        color: "var(--color-warn)",
        padding: "6px 12px",
        borderRadius: 999,
        fontSize: 12,
      }}
      aria-label={`${days} day streak`}
    >
      {/* Flame icon */}
      <svg
        width="13"
        height="13"
        viewBox="0 0 24 24"
        fill="currentColor"
        aria-hidden="true"
      >
        <path d="M12 2C12 2 7 7 7 13a5 5 0 0 0 10 0C17 7 12 2 12 2ZM12 18a3 3 0 0 1-3-3c0-2.5 2-5 3-7 1 2 3 4.5 3 7a3 3 0 0 1-3 3Z" />
      </svg>
      {days}d streak
    </span>
  );
}
