import type { ReactNode } from "react";
import TabBar from "@/components/shell/TabBar";

/**
 * Authenticated app shell.
 * Wraps children with a persistent bottom tab bar and a top safe-area spacer.
 * Login/onboarding routes live outside this group and have no tab bar.
 */
export default function AppLayout({ children }: { children: ReactNode }) {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        minHeight: "100dvh",
        position: "relative",
      }}
    >
      {/* Top safe-area spacer */}
      <div
        style={{
          position: "fixed",
          top: 0,
          left: 0,
          right: 0,
          height: "env(safe-area-inset-top, 0px)",
          zIndex: 40,
        }}
        aria-hidden="true"
      />
      {/* Main content — padded to clear the fixed tab bar */}
      <main className="pb-[var(--tab-h)]" style={{ flex: 1 }}>
        {children}
      </main>
      <TabBar />
    </div>
  );
}
