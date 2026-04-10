import type { ReactNode } from "react";

interface PageHeaderProps {
  /** Primary h1 title. Uses t-h1 class: 22px/700/−0.01em. */
  title: string;
  /** Optional subtitle line. 13px/500/ink-3 matching mockup .h-hello. */
  subtitle?: string;
  /** Optional trailing element (avatar, chip, action button). */
  trailing?: ReactNode;
  /** Bottom margin in px. Default 12. */
  mb?: number;
}

/**
 * Shared page-level header used by all main-tab screens.
 *
 * Renders a flex row with:
 *   - Left: optional subtitle `<p>` above `<h1 className="t-h1">`
 *   - Right: optional `trailing` slot (avatar, chip, action)
 *
 * Typography matches the mockup's .h-hello / .h-title definitions:
 *   - title:    22px / 700 / −0.01em tracking (via t-h1)
 *   - subtitle: 13px / 500 / ink-3
 *
 * Used inside ScreenFrame which already provides horizontal padding.
 * The `mb` prop controls spacing below the header before content begins.
 */
export function PageHeader({ title, subtitle, trailing, mb = 12 }: PageHeaderProps) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        paddingTop: 8,
        marginBottom: mb,
      }}
    >
      <div>
        {subtitle && (
          <p
            style={{
              fontSize: 13,
              fontWeight: 500,
              color: "var(--color-ink-3)",
              marginBottom: 2,
            }}
          >
            {subtitle}
          </p>
        )}
        <h1 className="t-h1" style={{ color: "var(--color-ink)" }}>
          {title}
        </h1>
      </div>

      {trailing && (
        <div style={{ flexShrink: 0 }}>{trailing}</div>
      )}
    </div>
  );
}
