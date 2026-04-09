import type { ReactNode } from "react";

interface ScreenFrameProps {
  children: ReactNode;
  className?: string;
}

/**
 * Scrollable container that accounts for the fixed top status area and
 * the bottom tab bar height. Use this as the content wrapper inside
 * (app) route pages.
 */
export default function ScreenFrame({ children, className = "" }: ScreenFrameProps) {
  return (
    <div
      style={{
        flex: 1,
        overflowY: "auto",
        overflowX: "hidden",
        paddingTop: "52px", // clears status bar / top safe area
        paddingBottom: "calc(var(--tab-h, 74px) + env(safe-area-inset-bottom, 0px) + 28px)",
      }}
      className={className}
    >
      {children}
    </div>
  );
}
