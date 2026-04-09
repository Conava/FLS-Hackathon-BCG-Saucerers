import * as React from "react";

export interface SectionHeaderProps {
  /** Section title — rendered ALL-CAPS via CSS */
  title: string;
  /** Optional right-side action element (e.g. "See all" link or Chip) */
  action?: React.ReactNode;
}

/**
 * ALL-CAPS section header with optional right-side action.
 * Margin: 14px top, 10px bottom — matches design spec `h-row`.
 */
export function SectionHeader({ title, action }: SectionHeaderProps) {
  return (
    <div
      className="flex items-center justify-between"
      style={{ margin: "14px 0 10px" }}
    >
      <h2 className="t-section text-ink">{title}</h2>
      {action && (
        <div className="t-support text-accent">{action}</div>
      )}
    </div>
  );
}
