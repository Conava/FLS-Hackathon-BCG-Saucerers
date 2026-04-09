"use client";

/**
 * RecordsQA — Client Component for plain-language Q&A over EHR records.
 *
 * Renders:
 * - AiDisclosureBanner (required on all AI screens)
 * - Text input + submit button
 * - Loading state while the request is in flight
 * - AI answer text with inline Citation chips for each source record
 */

import * as React from "react";
import { AiDisclosureBanner } from "@/components/design/AiDisclosureBanner";
import { Citation } from "@/components/design/Citation";
import { postRecordsQA } from "@/lib/api/client";
import type { RecordsQAResponse } from "@/lib/api/schemas";
import { COPY } from "@/lib/copy/copy";

export function RecordsQA() {
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
    } catch {
      setError(COPY.errors.generic);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 12,
      }}
    >
      {/* AI disclosure banner — required on every AI screen */}
      <AiDisclosureBanner />

      {/* Q&A card */}
      <div
        style={{
          borderRadius: 16,
          background: "var(--color-accent-lt)",
          border: "1px solid rgba(26, 107, 116, 0.18)",
          padding: "16px",
        }}
      >
        <form onSubmit={handleSubmit} style={{ display: "flex", gap: 8 }}>
          <input
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder={COPY.records.placeholder}
            style={{
              flex: 1,
              borderRadius: 10,
              border: "1px solid var(--color-border, #E5E3DF)",
              background: "var(--color-surface)",
              color: "var(--color-ink)",
              padding: "10px 14px",
              fontSize: 13,
              outline: "none",
            }}
            aria-label="Ask a question about your records"
            disabled={loading}
          />
          <button
            type="submit"
            disabled={loading || !question.trim()}
            style={{
              borderRadius: 10,
              background: "var(--color-accent)",
              color: "#fff",
              border: "none",
              padding: "10px 18px",
              fontSize: 13,
              fontWeight: 600,
              cursor: loading ? "wait" : "pointer",
              opacity: !question.trim() ? 0.5 : 1,
            }}
            aria-label="Ask"
          >
            Ask
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
            Thinking…
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

        {/* Answer section */}
        {response && !loading && (
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
                      // Future: open record detail sheet
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
