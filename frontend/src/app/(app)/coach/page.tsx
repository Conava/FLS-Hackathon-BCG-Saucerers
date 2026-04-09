/**
 * Coach screen — AI Wellness Coach chat.
 *
 * Layout matches mockup section #s-coach:
 * 1. Header  — h1 "Coach" (22px/700) + subtitle (13px/500/ink-3)
 * 2. AI disclosure banner — non-dismissible, violet-lt bg, circuit icon
 * 3. CoachChat — scrollable log + suggestions + input + footer
 *
 * The optional `q` search param (e.g. from the Records tab Q&A input) is read
 * via `useSearchParams` inside a Suspense boundary (required by Next.js 15 for
 * client components that call useSearchParams). When present, CoachChat
 * prefills and auto-sends the question as the first message.
 *
 * Stack: Next.js 15 App Router, Tailwind v4.
 */

import * as React from "react";
import { AiDisclosureBanner } from "@/components/design";
import { CoachChatWithQuery } from "./chat";
import { PageHeader } from "@/components/shell/PageHeader";

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
          padding: "52px 20px 12px",
          borderBottom: "1px solid var(--color-border)",
          background: "var(--color-bg)",
          flexShrink: 0,
        }}
      >
        {/* Title + subtitle via shared PageHeader */}
        <PageHeader
          title="Coach"
          subtitle="Your longevity AI · personalized to your data"
          mb={10}
        />

        {/* AI disclosure — required on all AI screens, non-dismissible */}
        <AiDisclosureBanner />
      </header>

      {/* Scrollable chat area — fills remaining height */}
      <div
        style={{ flex: 1, overflow: "hidden", display: "flex", flexDirection: "column" }}
      >
        {/*
          Suspense boundary is required by Next.js 15 when useSearchParams is
          used inside a client component that is a direct descendant of a page.
        */}
        <React.Suspense fallback={null}>
          <CoachChatWithQuery />
        </React.Suspense>
      </div>
    </div>
  );
}
