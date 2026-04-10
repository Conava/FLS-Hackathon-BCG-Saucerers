import * as React from "react";

export interface EmptyStateProps {
  /** Icon element (SVG or emoji), displayed in a tinted box */
  icon?: React.ReactNode;
  /** Main heading */
  heading: string;
  /** Supporting subtext */
  subtext?: string;
  /** Optional action element, e.g. a Button */
  action?: React.ReactNode;
}

/**
 * Generic empty state with a centered icon box, heading, and optional subtext + action.
 */
export function EmptyState({ icon, heading, subtext, action }: EmptyStateProps) {
  return (
    <div
      className="flex flex-col items-center"
      style={{ textAlign: "center", padding: "30px 16px", color: "var(--color-ink-3)" }}
    >
      {icon && (
        <div
          className="flex items-center justify-center"
          style={{
            width: 56,
            height: 56,
            borderRadius: 16,
            background: "var(--color-bg-2)",
            marginBottom: 10,
            color: "var(--color-ink-3)",
          }}
          aria-hidden="true"
        >
          {icon}
        </div>
      )}

      <p
        style={{
          fontSize: 13,
          fontWeight: 600,
          color: "var(--color-ink-2)",
        }}
      >
        {heading}
      </p>

      {subtext && (
        <p className="t-caption" style={{ marginTop: 4 }}>
          {subtext}
        </p>
      )}

      {action && <div style={{ marginTop: 16 }}>{action}</div>}
    </div>
  );
}
