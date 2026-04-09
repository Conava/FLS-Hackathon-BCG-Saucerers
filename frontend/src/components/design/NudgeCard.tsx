import * as React from "react";

export interface NudgeCardProps {
  /** Contextual sentence headline, e.g. "You slept 5h 40m last night" */
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
 *
 * Visuals match mockup `.nudge`:
 *   - amber gradient background (warn-lt family)
 *   - 34×34 icon container with warn accent
 *   - 13px/700 title, 11.5px/ink-2 body with 1.55 line-height
 *   - primary + ghost CTA buttons sized to match btn-sm
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
      style={{
        background:
          "linear-gradient(135deg, #FFF7E8 0%, var(--color-warn-lt) 100%)",
        border: "1px solid #F3DFA6",
        borderRadius: "var(--radius-md)",
        padding: 14,
        display: "flex",
        gap: 12,
      }}
    >
      {/* Icon box — 34×34, warn accent */}
      <div
        style={{
          width: 34,
          height: 34,
          borderRadius: 10,
          background: "#F3DFA6",
          color: "var(--color-warn)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          flexShrink: 0,
        }}
        aria-hidden="true"
      >
        {/* Bell / alert icon */}
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

      {/* Content column */}
      <div style={{ flex: 1, minWidth: 0 }}>
        {/* Title — 13px, bold, ink */}
        <p
          style={{
            fontSize: 13,
            fontWeight: 700,
            lineHeight: 1.35,
            color: "var(--color-ink)",
            margin: 0,
          }}
        >
          {title}
        </p>

        {/* Description — 11.5px, ink-2, 1.55 line-height */}
        <p
          style={{
            fontSize: 11.5,
            color: "var(--color-ink-2)",
            lineHeight: 1.55,
            margin: "2px 0 0",
          }}
        >
          {description}
        </p>

        {/* CTA row */}
        {(ctaLabel || secondaryLabel) && (
          <div style={{ display: "flex", gap: 8, marginTop: 10 }}>
            {ctaLabel && (
              <button
                type="button"
                onClick={onCta}
                style={{
                  padding: "7px 12px",
                  fontSize: 12.5,
                  fontWeight: 600,
                  lineHeight: 1,
                  background: "var(--color-accent)",
                  color: "#fff",
                  border: "1px solid transparent",
                  borderRadius: "var(--radius-sm)",
                  cursor: "pointer",
                  whiteSpace: "nowrap",
                }}
              >
                {ctaLabel}
              </button>
            )}
            {secondaryLabel && (
              <button
                type="button"
                onClick={onSecondary}
                style={{
                  padding: "7px 12px",
                  fontSize: 12.5,
                  fontWeight: 600,
                  lineHeight: 1,
                  background: "var(--color-surface)",
                  color: "var(--color-ink)",
                  border: "1px solid var(--color-border)",
                  borderRadius: "var(--radius-sm)",
                  cursor: "pointer",
                  whiteSpace: "nowrap",
                }}
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
