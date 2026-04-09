import type { ReactNode } from "react";

interface ScreenFrameProps {
  children: ReactNode;
  className?: string;
  /**
   * Horizontal padding in px. Default 20 matches mockup .screen padding.
   * Pass 0 for screens needing full-bleed layout (e.g. Coach chat area).
   */
  px?: number;
}

/**
 * Scrollable container that accounts for the fixed top status area and
 * the bottom tab bar height. Use this as the content wrapper inside
 * (app) route pages.
 *
 * The `px` prop controls horizontal padding (default: 20px, matching
 * the mockup's .screen padding). Pass 0 for full-bleed layouts.
 */
export default function ScreenFrame({ children, className = "", px = 20 }: ScreenFrameProps) {
  return (
    <div
      style={{
        flex: 1,
        overflowY: "auto",
        overflowX: "hidden",
        paddingTop: "52px", // clears status bar / top safe area
        paddingBottom: "calc(var(--tab-h, 74px) + env(safe-area-inset-bottom, 0px) + 28px)",
        paddingLeft: px,
        paddingRight: px,
      }}
      className={className}
    >
      {children}
    </div>
  );
}
