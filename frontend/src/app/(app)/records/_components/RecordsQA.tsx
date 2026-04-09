"use client";

/**
 * RecordsQA — Client Component for routing record questions to the Coach tab.
 *
 * Renders:
 * - AI disclosure banner with file icon, "EHR-scoped" pill, and violet-lt bg
 * - Q&A card (accent-lt bg, accent-md border) with heading, subtext, chat input
 *
 * On submit, the question is URL-encoded and the user is navigated to
 * `/coach?q=<question>` where the Coach tab will auto-send it as the first
 * message of a new conversation.
 */

import * as React from "react";
import { useRouter } from "next/navigation";
import { COPY } from "@/lib/copy/copy";

export function RecordsQA() {
  const router = useRouter();
  const [question, setQuestion] = React.useState("");

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = question.trim();
    if (!trimmed) return;
    router.push(`/coach?q=${encodeURIComponent(trimmed)}`);
  }

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 12,
      }}
    >
      {/* AI disclosure banner */}
      <div
        role="note"
        className="flex items-center"
        style={{
          padding: "10px 14px",
          borderRadius: 14,
          background: "var(--color-violet-lt)",
          color: "var(--color-violet)",
          border: "1px solid rgba(107, 74, 168, 0.18)",
          fontSize: 11.5,
          fontWeight: 600,
          gap: 10,
        }}
      >
        {/* File document icon */}
        <svg
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          aria-hidden="true"
          style={{ flexShrink: 0 }}
        >
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
          <path d="M14 2v6h6" />
        </svg>

        <span>
          <span>You&apos;re talking to an AI</span>
          <span style={{ opacity: 0.75 }}>
            {" "}
            &middot; Records Q&amp;A is AI &middot; answers cite real documents &middot; Gemini 2.5
            Pro
          </span>
        </span>

        {/* EHR-scoped pill */}
        <span
          className="ml-auto"
          style={{
            fontSize: 10,
            opacity: 0.85,
            flexShrink: 0,
          }}
        >
          EHR-scoped
        </span>
      </div>

      {/* Q&A card */}
      <div
        style={{
          borderRadius: 16,
          background: "var(--color-accent-lt)",
          border: "1px solid var(--color-accent-md)",
          padding: "16px",
        }}
      >
        {/* Card heading */}
        <div style={{ fontSize: 12.5, fontWeight: 700, color: "var(--color-ink)" }}>
          Ask about your records
        </div>

        {/* Card subtext */}
        <div
          style={{
            fontSize: 11.5,
            color: "var(--color-ink-2)",
            margin: "4px 0 10px",
          }}
        >
          Plain-language answers, citing the actual lab or report.
        </div>

        {/* Chat input — white background inside the accent card */}
        <form
          onSubmit={handleSubmit}
          style={{
            display: "flex",
            gap: 8,
            background: "#fff",
            borderRadius: 10,
            border: "1px solid var(--color-border)",
            padding: "4px 4px 4px 12px",
          }}
        >
          <input
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder={COPY.records.placeholder}
            style={{
              flex: 1,
              border: "none",
              background: "transparent",
              color: "var(--color-ink)",
              fontSize: 13,
              outline: "none",
              padding: "6px 0",
            }}
            aria-label="Ask a question about your records"
          />
          <button
            type="submit"
            disabled={!question.trim()}
            style={{
              borderRadius: 8,
              background: "var(--color-accent)",
              color: "#fff",
              border: "none",
              padding: "8px 14px",
              fontSize: 13,
              fontWeight: 600,
              cursor: "pointer",
              opacity: !question.trim() ? 0.5 : 1,
              display: "flex",
              alignItems: "center",
            }}
            aria-label="Ask"
          >
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="#fff"
              strokeWidth="2.5"
              strokeLinecap="round"
              aria-hidden="true"
            >
              <path d="M5 12h14M13 6l6 6-6 6" />
            </svg>
          </button>
        </form>
      </div>
    </div>
  );
}
