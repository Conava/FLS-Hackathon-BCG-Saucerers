"use client";

/**
 * RecordsQA — Client Component for plain-language Q&A over EHR records.
 *
 * Renders:
 * - AI disclosure banner with file icon, "EHR-scoped" pill, and violet-lt bg
 * - Q&A card (accent-lt bg, accent-md border) with heading, subtext, chat input
 * - Loading state while the request is in flight
 * - Inline answer with Citation chips (when used standalone, i.e. no onAnswer)
 *
 * When `onAnswer` is provided, the parent component owns the response display
 * (used by RecordsContent to render the answer in a separate summary card).
 * When omitted, the component renders its own answer inline (backward-compatible).
 */

import * as React from "react";
import { Citation } from "@/components/design/Citation";
import { postRecordsQA } from "@/lib/api/client";
import type { RecordsQAResponse } from "@/lib/api/schemas";
import { COPY } from "@/lib/copy/copy";

export interface RecordsQAProps {
  /**
   * Optional callback invoked when the API returns a successful answer.
   * When provided the parent controls the answer display; the inline answer
   * section is suppressed.
   */
  onAnswer?: (response: RecordsQAResponse) => void;
}

export function RecordsQA({ onAnswer }: RecordsQAProps) {
  const [question, setQuestion] = React.useState("");
  const [loading, setLoading] = React.useState(false);
  const [response, setResponse] = React.useState<RecordsQAResponse | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = question.trim();
    if (!trimmed) return;

    setLoading(true);
    setError(null);
    setResponse(null);

    try {
      const result = await postRecordsQA(trimmed);
      setResponse(result);
      onAnswer?.(result);
    } catch {
      setError(COPY.errors.generic);
    } finally {
      setLoading(false);
    }
  }

  // Whether to show the inline answer (only when not delegating to parent)
  const showInlineAnswer = !onAnswer;

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
            disabled={loading}
          />
          <button
            type="submit"
            disabled={loading || !question.trim()}
            style={{
              borderRadius: 8,
              background: "var(--color-accent)",
              color: "#fff",
              border: "none",
              padding: "8px 14px",
              fontSize: 13,
              fontWeight: 600,
              cursor: loading ? "wait" : "pointer",
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

        {/* Loading indicator */}
        {loading && (
          <div
            role="status"
            aria-live="polite"
            style={{
              marginTop: 12,
              fontSize: 12,
              color: "var(--color-accent)",
              fontWeight: 600,
            }}
          >
            Thinking&hellip;
          </div>
        )}

        {/* Error state */}
        {error && !loading && (
          <p
            role="alert"
            style={{
              marginTop: 12,
              fontSize: 12,
              color: "var(--color-danger)",
            }}
          >
            {error}
          </p>
        )}

        {/* Inline answer section — only when not delegating to parent */}
        {showInlineAnswer && response && !loading && (
          <div style={{ marginTop: 14 }}>
            <p
              style={{
                fontSize: 13,
                color: "var(--color-ink)",
                lineHeight: 1.6,
              }}
            >
              {response.answer}
            </p>

            {/* Citation chips */}
            {response.citations && response.citations.length > 0 && (
              <div
                style={{
                  marginTop: 10,
                  display: "flex",
                  flexWrap: "wrap",
                  gap: 4,
                  alignItems: "center",
                }}
              >
                <span
                  style={{
                    fontSize: 10.5,
                    color: "var(--color-ink-3)",
                    fontWeight: 600,
                  }}
                >
                  Sources:
                </span>
                {response.citations.map((citation, index) => (
                  <Citation
                    key={citation.record_id}
                    label={index + 1}
                    onClick={() => {
                      console.info(`Open record ${citation.record_id}`);
                    }}
                  />
                ))}
              </div>
            )}

            {/* Disclaimer if present */}
            {response.disclaimer && (
              <p
                style={{
                  marginTop: 8,
                  fontSize: 10.5,
                  color: "var(--color-ink-3)",
                  fontStyle: "italic",
                }}
              >
                {response.disclaimer}
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
