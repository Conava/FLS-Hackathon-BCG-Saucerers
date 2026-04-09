"use client";

import * as React from "react";
import { ChatBubble } from "@/components/design/ChatBubble";
import { TypingIndicator } from "@/components/design/TypingIndicator";
import { SuggestedChip } from "@/components/design/Chip";
import { coachChat } from "@/lib/api/client";
import { COPY } from "@/lib/copy/copy";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface Message {
  role: "user" | "ai";
  content: string;
}

export interface CoachChatProps {
  /**
   * Optional initial list of suggested prompt chips shown when the thread is
   * empty. Tapping a chip pre-fills the input.
   */
  suggestions?: string[];
}

// Default suggestions shown on an empty thread
const DEFAULT_SUGGESTIONS = [
  "How can I improve my sleep?",
  "What does my vitality score mean?",
  "Give me today's top wellness tip",
  "How is my cardiovascular health?",
];

// ---------------------------------------------------------------------------
// CoachChat
// ---------------------------------------------------------------------------

/**
 * Full-screen chat client component for the AI Wellness Coach.
 *
 * - Streams token-by-token via `coachChat` (SSE-backed AsyncIterable).
 * - Shows `TypingIndicator` while waiting for the first token.
 * - Appends tokens to the last AI bubble as they arrive.
 * - Handles errors gracefully by inserting an error bubble.
 * - Suggested chips pre-fill the input; hidden once the thread has messages.
 * - Auto-scrolls to the bottom on new content unless the user has scrolled up.
 */
export function CoachChat({ suggestions = DEFAULT_SUGGESTIONS }: CoachChatProps) {
  const [messages, setMessages] = React.useState<Message[]>([]);
  const [input, setInput] = React.useState("");
  const [streaming, setStreaming] = React.useState(false);
  const [waitingForFirst, setWaitingForFirst] = React.useState(false);
  const [isStreaming, setIsStreaming] = React.useState(false);

  const listRef = React.useRef<HTMLDivElement>(null);
  const userScrolledUp = React.useRef(false);

  // ── Autoscroll ─────────────────────────────────────────────────────────────

  const scrollToBottom = React.useCallback(() => {
    if (userScrolledUp.current) return;
    const el = listRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, []);

  React.useEffect(() => {
    scrollToBottom();
  }, [messages, waitingForFirst, scrollToBottom]);

  const handleScroll = React.useCallback(() => {
    const el = listRef.current;
    if (!el) return;
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 40;
    userScrolledUp.current = !atBottom;
  }, []);

  // ── Send ────────────────────────────────────────────────────────────────────

  const handleSend = React.useCallback(
    async (text: string) => {
      const trimmed = text.trim();
      if (!trimmed || isStreaming) return;

      // Build history (existing messages before the new one)
      const history = messages.map((m) => ({
        role: m.role === "ai" ? "assistant" : "user",
        content: m.content,
      }));

      // Append user message
      const userMsg: Message = { role: "user", content: trimmed };
      setMessages((prev) => [...prev, userMsg]);
      setInput("");
      userScrolledUp.current = false;

      setWaitingForFirst(true);
      setIsStreaming(true);

      try {
        const stream = coachChat({ message: trimmed, history });

        // Insert empty AI bubble
        setMessages((prev) => [...prev, { role: "ai", content: "" }]);
        setStreaming(true);

        for await (const chunk of stream) {
          if (chunk.event === "token") {
            setWaitingForFirst(false);
            setMessages((prev) => {
              const next = [...prev];
              const last = next[next.length - 1];
              if (last && last.role === "ai") {
                next[next.length - 1] = {
                  ...last,
                  content: last.content + chunk.data,
                };
              }
              return next;
            });
          } else if (chunk.event === "done") {
            break;
          } else if (chunk.event === "error") {
            setMessages((prev) => {
              const next = [...prev];
              next[next.length - 1] = {
                role: "ai",
                content: COPY.coach.errorReply,
              };
              return next;
            });
            break;
          }
        }
      } catch {
        // Replace placeholder bubble with error copy
        setMessages((prev) => {
          const next = [...prev];
          const last = next[next.length - 1];
          if (last && last.role === "ai") {
            next[next.length - 1] = {
              role: "ai",
              content: COPY.coach.errorReply,
            };
          } else {
            next.push({ role: "ai", content: COPY.coach.errorReply });
          }
          return next;
        });
      } finally {
        setStreaming(false);
        setWaitingForFirst(false);
        setIsStreaming(false);
      }

    },
    [messages, isStreaming]
  );

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    void handleSend(input);
  };

  const handleChipClick = (label: string) => {
    setInput(label);
  };

  // ── Render ──────────────────────────────────────────────────────────────────

  const showSuggestions = messages.length === 0 && !isStreaming;

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100%",
        minHeight: 0,
        flex: 1,
      }}
    >
      {/* ── Message list ─────────────────────────────────────────────────── */}
      <div
        ref={listRef}
        onScroll={handleScroll}
        style={{
          flex: 1,
          overflowY: "auto",
          padding: "16px 16px 8px",
          display: "flex",
          flexDirection: "column",
          gap: 10,
        }}
        aria-label="Chat messages"
      >
        {messages.map((msg, i) => {
          const isLast = i === messages.length - 1;
          const isStreamingBubble = isLast && msg.role === "ai" && streaming;
          return (
            <ChatBubble
              key={i}
              role={msg.role}
              content={msg.content}
              streaming={isStreamingBubble}
            />
          );
        })}

        {/* TypingIndicator — shown before first token arrives */}
        {waitingForFirst && <TypingIndicator />}
      </div>

      {/* ── Suggested chips ──────────────────────────────────────────────── */}
      {showSuggestions && (
        <div
          style={{
            padding: "0 16px 12px",
            display: "flex",
            flexWrap: "wrap",
            gap: 8,
          }}
          aria-label="Suggested questions"
        >
          {suggestions.map((s) => (
            <SuggestedChip key={s} label={s} onClick={() => handleChipClick(s)} />
          ))}
        </div>
      )}

      {/* ── Input bar ────────────────────────────────────────────────────── */}
      <form
        onSubmit={handleSubmit}
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          padding: "12px 16px",
          paddingBottom: "calc(12px + env(safe-area-inset-bottom, 0px))",
          borderTop: "1px solid var(--color-border)",
          background: "var(--color-bg)",
          position: "sticky",
          bottom: 0,
        }}
        aria-label="Send a message"
      >
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={COPY.coach.placeholder}
          disabled={isStreaming}
          aria-label="Message input"
          style={{
            flex: 1,
            padding: "10px 14px",
            borderRadius: 999,
            border: "1px solid var(--color-border)",
            background: "var(--color-surface)",
            color: "var(--color-ink)",
            fontSize: 14,
            outline: "none",
          }}
        />

        {/* Send button */}
        <button
          type="submit"
          disabled={!input.trim() || isStreaming}
          aria-label={COPY.coach.sendButton}
          style={{
            width: 40,
            height: 40,
            borderRadius: "50%",
            background: "var(--color-accent)",
            color: "#fff",
            border: "none",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            flexShrink: 0,
            cursor: input.trim() && !isStreaming ? "pointer" : "not-allowed",
            opacity: input.trim() && !isStreaming ? 1 : 0.5,
          }}
        >
          {/* Arrow-up icon */}
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <line x1="12" y1="19" x2="12" y2="5" />
            <polyline points="5 12 12 5 19 12" />
          </svg>
        </button>
      </form>
    </div>
  );
}
