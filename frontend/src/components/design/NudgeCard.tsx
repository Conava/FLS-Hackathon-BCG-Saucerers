import * as React from "react";

export interface NudgeCardProps {
  /** Short headline, e.g. "Hydration reminder" */
  title: string;
  /** Descriptive body text */
  description: string;
  /** Optional primary CTA label */
  ctaLabel?: string;
  /** Called when the primary CTA is tapped */
  onCta?: () => void;
  /** Optional secondary action label */
  secondaryLabel?: string;
  /** Called when the secondary action is tapped */
  onSecondary?: () => void;
}

/**
 * Contextual warning-tone nudge card shown on the Today screen.
 * Has an amber gradient background matching the warn color family.
 */
export function NudgeCard({
  title,
  description,
  ctaLabel,
  onCta,
  secondaryLabel,
  onSecondary,
}: NudgeCardProps) {
  return (
    <div
      role="alert"
      className="flex gap-3 rounded-[14px]"
      style={{
        background: "linear-gradient(135deg, #FFF7E8 0%, #FDF3DC 100%)",
        border: "1px solid #F3DFA6",
        padding: 14,
      }}
    >
      {/* Icon box */}
      <div
        className="flex-shrink-0 flex items-center justify-center rounded-[10px]"
        style={{
          width: 34,
          height: 34,
          background: "#F3DFA6",
          color: "var(--color-warn)",
        }}
        aria-hidden="true"
      >
        {/* Warning / bell icon */}
        <svg
          width="18"
          height="18"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
          <path d="M13.73 21a2 2 0 0 1-3.46 0" />
        </svg>
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <p className="t-body-sm font-bold text-ink">{title}</p>
        <p className="t-caption text-ink-2" style={{ marginTop: 2 }}>
          {description}
        </p>

        {(ctaLabel || secondaryLabel) && (
          <div className="flex gap-2" style={{ marginTop: 10 }}>
            {ctaLabel && (
              <button
                type="button"
                onClick={onCta}
                className="t-support text-accent font-semibold"
              >
                {ctaLabel}
              </button>
            )}
            {secondaryLabel && (
              <button
                type="button"
                onClick={onSecondary}
                className="t-support text-ink-3"
              >
                {secondaryLabel}
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
