/**
 * Coach screen — AI Wellness Coach chat.
 *
 * Layout matches mockup section #s-coach:
 * 1. Header  — h1 "Coach" (22px/700) + subtitle (13px/500/ink-3)
 * 2. AI disclosure banner — non-dismissible, violet-lt bg, circuit icon
 * 3. CoachChat — scrollable log + suggestions + input + footer
 *
 * Stack: Next.js 15 App Router, Tailwind v4.
 */

import { AiDisclosureBanner } from "@/components/design";
import { CoachChat } from "./chat";

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
          padding: "52px 16px 12px",
          borderBottom: "1px solid var(--color-border)",
          background: "var(--color-bg)",
          flexShrink: 0,
        }}
      >
        {/* h1 "Coach" — 22px / 700, matches mockup .h-title */}
        <h1
          style={{
            fontSize: 22,
            fontWeight: 700,
            letterSpacing: "-0.01em",
            color: "var(--color-ink)",
            marginBottom: 4,
          }}
        >
          Coach
        </h1>

        {/* Subtitle — 13px / 500 / ink-3, matches mockup .h-hello */}
        <p
          style={{
            fontSize: 13,
            fontWeight: 500,
            color: "var(--color-ink-3)",
            marginBottom: 10,
          }}
        >
          Your longevity AI · personalized to your data
        </p>

        {/* AI disclosure — required on all AI screens, non-dismissible */}
        <AiDisclosureBanner />
      </header>

      {/* Scrollable chat area — fills remaining height */}
      <div
        style={{ flex: 1, overflow: "hidden", display: "flex", flexDirection: "column" }}
      >
        <CoachChat />
      </div>
    </div>
  );
}
