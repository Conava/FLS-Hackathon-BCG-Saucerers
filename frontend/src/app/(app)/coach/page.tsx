/**
 * Coach screen — AI Wellness Coach chat.
 *
 * Server Component wrapper that renders the CoachChat client component.
 * The AiDisclosureBanner is required on all AI-powered screens.
 *
 * Stack: Next.js 15 App Router, Tailwind v4.
 */

import { AiDisclosureBanner } from "@/components/design";
import { CoachChat } from "./chat";
import { COPY } from "@/lib/copy/copy";

export default function CoachPage() {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100dvh",
        overflow: "hidden",
      }}
    >
      {/* Page header */}
      <header
        style={{
          padding: "52px 16px 8px",
          borderBottom: "1px solid var(--color-border)",
          background: "var(--color-bg)",
          flexShrink: 0,
        }}
      >
        <h1
          className="t-h1 text-ink"
          style={{ fontSize: 20, fontWeight: 700, marginBottom: 4 }}
        >
          {COPY.coach.sessionTitle}
        </h1>
        {/* AI disclosure — required on this screen */}
        <AiDisclosureBanner />
      </header>

      {/* Scrollable chat area — fills remaining height */}
      <div style={{ flex: 1, overflow: "hidden", display: "flex", flexDirection: "column" }}>
        <CoachChat />
      </div>
    </div>
  );
}
