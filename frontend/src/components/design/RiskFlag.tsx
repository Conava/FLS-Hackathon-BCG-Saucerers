import * as React from "react";

export type RiskLevel = "warn" | "danger";

export interface RiskFlagProps {
  /** Title of the risk */
  title: string;
  /** Explanatory body text */
  description: string;
  /** Severity level — warn (amber) or danger (red) */
  level?: RiskLevel;
  /** Optional action label */
  ctaLabel?: string;
  /** Called when CTA is tapped */
  onCta?: () => void;
}

const LEVEL_STYLES: Record<
  RiskLevel,
  { borderColor: string; iconBg: string; iconColor: string }
> = {
  warn: {
    borderColor: "var(--color-warn)",
    iconBg: "var(--color-warn-lt)",
    iconColor: "var(--color-warn)",
  },
  danger: {
    borderColor: "var(--color-danger)",
    iconBg: "var(--color-danger-lt)",
    iconColor: "var(--color-danger)",
  },
};

/**
 * Amber or red risk flag card displayed on the Insights screen.
 */
export function RiskFlag({
  title,
  description,
  level = "warn",
  ctaLabel,
  onCta,
}: RiskFlagProps) {
  const styles = LEVEL_STYLES[level];

  return (
    <div
      role="alert"
      className="bg-surface flex gap-3 rounded-[14px]"
      style={{
        padding: 14,
        border: `1px solid var(--color-border)`,
        borderLeft: `4px solid ${styles.borderColor}`,
      }}
    >
      {/* Icon */}
      <div
        className="flex-shrink-0 flex items-center justify-center rounded-[8px]"
        style={{
          width: 34,
          height: 34,
          background: styles.iconBg,
          color: styles.iconColor,
        }}
        aria-hidden="true"
      >
        <svg
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0Z" />
          <line x1="12" y1="9" x2="12" y2="13" />
          <line x1="12" y1="17" x2="12.01" y2="17" />
        </svg>
      </div>

      {/* Content */}
      <div className="flex-1">
        <p className="t-body-sm font-bold text-ink">{title}</p>
        <p className="t-caption text-ink-2" style={{ marginTop: 2 }}>
          {description}
        </p>
        {ctaLabel && (
          <button
            type="button"
            onClick={onCta}
            className="t-support font-semibold"
            style={{ color: styles.borderColor, marginTop: 8 }}
          >
            {ctaLabel}
          </button>
        )}
      </div>
    </div>
  );
}
