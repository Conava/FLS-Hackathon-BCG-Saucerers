"use client";

/**
 * MessageComposer — client component for posting a new care-team message.
 *
 * Calls POST /api/proxy/messages via the Next.js proxy route which injects
 * the patient_id from the httpOnly cookie server-side.
 */

import * as React from "react";
import { COPY } from "@/lib/copy/copy";

/** POST /api/proxy/messages */
async function postMessage(content: string): Promise<void> {
  const res = await fetch("/api/proxy/messages", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content }),
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`Failed to send message: ${res.status} ${text}`);
  }
}

/**
 * Text input + send button for the messages thread.
 * On success the input is cleared.
 */
export function MessageComposer() {
  const [value, setValue] = React.useState("");
  const [sending, setSending] = React.useState(false);

  const handleSend = async () => {
    const trimmed = value.trim();
    if (!trimmed || sending) return;

    setSending(true);
    try {
      await postMessage(trimmed);
      setValue("");
    } finally {
      setSending(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void handleSend();
    }
  };

  return (
    <div
      className="flex gap-2 items-end"
      style={{
        padding: "12px 0 4px",
        borderTop: "1px solid var(--color-border)",
        marginTop: 8,
      }}
    >
      <textarea
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={COPY.coach.inputHint}
        rows={1}
        aria-label="Message"
        disabled={sending}
        style={{
          flex: 1,
          resize: "none",
          padding: "10px 14px",
          borderRadius: 14,
          border: "1px solid var(--color-border)",
          fontSize: 14,
          lineHeight: 1.5,
          background: "var(--color-surface)",
          color: "var(--color-ink)",
          outline: "none",
        }}
      />
      <button
        type="button"
        onClick={() => void handleSend()}
        disabled={!value.trim() || sending}
        aria-label="Send"
        style={{
          flexShrink: 0,
          width: 44,
          height: 44,
          borderRadius: 14,
          background:
            !value.trim() || sending
              ? "var(--color-bg-2)"
              : "var(--color-accent)",
          color: !value.trim() || sending ? "var(--color-ink-3)" : "#fff",
          border: "none",
          cursor: !value.trim() || sending ? "default" : "pointer",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          transition: "background 0.15s",
        }}
      >
        {/* Send arrow icon */}
        <svg
          width="18"
          height="18"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.2"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <line x1="22" y1="2" x2="11" y2="13" />
          <polygon points="22 2 15 22 11 13 2 9 22 2" />
        </svg>
        <span className="sr-only">Send</span>
      </button>
    </div>
  );
}
