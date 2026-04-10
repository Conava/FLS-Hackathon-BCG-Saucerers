"use client";

import * as React from "react";
import { useSearchParams } from "next/navigation";
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

  /**
   * Optional pre-filled message to auto-send on mount (used when navigating
   * from the Records tab with a prefilled question).
   */
  initialMessage?: string;
}

// Default suggestions shown on an empty thread — matches mockup
const DEFAULT_SUGGESTIONS = [
  "What should I eat for lower ApoB?",
  "Plan my week",
  "I feel stressed",
  "Recipe for dinner",
];

// ---------------------------------------------------------------------------
// CoachChatWithQuery
// ---------------------------------------------------------------------------

/**
 * Thin wrapper that reads the `q` search param and passes it to CoachChat as
 * `initialMessage`. Placed inside a Suspense boundary in the page so that
 * useSearchParams doesn't block the static shell.
 *
 * After consuming the param, the URL is cleaned up via replaceState so a page
 * reload won't re-submit the question.
 */
export function CoachChatWithQuery() {
  const searchParams = useSearchParams();

  const q = searchParams.get("q") ?? undefined;

  // Clear the `q` param from the URL immediately so reloading doesn't re-send
  React.useEffect(() => {
    if (q) {
      // replaceState keeps the history entry but removes the query param
      const url = new URL(window.location.href);
      url.searchParams.delete("q");
      window.history.replaceState(null, "", url.toString());
    }
    // Only run once on mount — intentionally omitting `q` and `router` deps
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return <CoachChat initialMessage={q} />;
}

// ---------------------------------------------------------------------------
// CoachChat
// ---------------------------------------------------------------------------

/**
 * Full-screen chat client component for the AI Wellness Coach.
 *
 * Matches mockup layout in order:
 * - Scrollable message log (.chat-log): gap 12px, flex column
 * - Suggested prompt chips (.suggest): horizontal scroll, hidden once thread has messages
 * - Input form (.chat-input): outer 999px-radius container with voice + send buttons
 * - Footer disclaimer (.fine): 11.5px / ink-3
 *
 * Streaming behaviour:
 * - Shows `TypingIndicator` while waiting for the first token.
 * - Appends tokens to the last AI bubble as they arrive.
 * - Last streaming AI bubble shows a blinking cursor.
 * - Handles errors gracefully by inserting an error bubble.
 * - Auto-scrolls to the bottom on new content unless the user has scrolled up.
 *
 * When `initialMessage` is provided the component auto-sends it on mount,
 * simulating a user submission. This is used when navigating from the Records
 * tab Q&A input.
 */
export function CoachChat({
  suggestions = DEFAULT_SUGGESTIONS,
  initialMessage,
}: CoachChatProps) {
  const [messages, setMessages] = React.useState<Message[]>([]);
  const [input, setInput] = React.useState("");
  const [streaming, setStreaming] = React.useState(false);
  const [waitingForFirst, setWaitingForFirst] = React.useState(false);
  const [isStreaming, setIsStreaming] = React.useState(false);

  const listRef = React.useRef<HTMLDivElement>(null);
  const userScrolledUp = React.useRef(false);
  const autoSentRef = React.useRef(false);

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

  // ── Auto-send initialMessage on mount ──────────────────────────────────────

  React.useEffect(() => {
    if (initialMessage && !autoSentRef.current) {
      autoSentRef.current = true;
      void handleSend(initialMessage);
    }
    // handleSend identity changes with messages/isStreaming, but we only want
    // to fire this once on mount, so we suppress the dep warning.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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
      {/* ── Message log (.chat-log) ──────────────────────────────────────── */}
      <div
        ref={listRef}
        onScroll={handleScroll}
        style={{
          flex: 1,
          overflowY: "auto",
          padding: "16px 16px 8px",
          display: "flex",
          flexDirection: "column",
          gap: 12,
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

      {/* ── Suggested prompt chips (.suggest) — horizontal scroll ────────── */}
      {showSuggestions && (
        <div
          style={{
            display: "flex",
            gap: 8,
            padding: "0 16px 10px",
            overflowX: "auto",
            WebkitOverflowScrolling: "touch",
            scrollbarWidth: "none",
          }}
          aria-label="Suggested questions"
        >
          {suggestions.map((s) => (
            <SuggestedChip
              key={s}
              label={s}
              style={{ flexShrink: 0, whiteSpace: "nowrap" }}
              onClick={() => handleChipClick(s)}
            />
          ))}
        </div>
      )}

      {/* ── Input bar (.chat-input) — outer rounded container ────────────── */}
      <form
        onSubmit={handleSubmit}
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          margin: "0 12px",
          padding: "10px 12px",
          background: "var(--color-surface)",
          border: "1px solid var(--color-border)",
          borderRadius: 999,
          marginBottom: `calc(12px + env(safe-area-inset-bottom, 0px))`,
        }}
        aria-label="Send a message"
      >
        {/* Text input — bare, no border */}
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={COPY.coach.placeholder}
          disabled={isStreaming}
          aria-label="Message input"
          style={{
            flex: 1,
            border: "none",
            background: "transparent",
            outline: "none",
            fontSize: 14,
            fontFamily: "inherit",
            color: "var(--color-ink)",
            minWidth: 0,
          }}
        />

        {/* Voice button — transparent bg, ink-3 icon */}
        <button
          type="button"
          aria-label="Voice input"
          style={{
            width: 36,
            height: 36,
            borderRadius: 999,
            border: "none",
            background: "transparent",
            color: "var(--color-ink-3)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            flexShrink: 0,
            cursor: "pointer",
            padding: 0,
          }}
        >
          <svg
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <rect x="9" y="3" width="6" height="12" rx="3" />
            <path d="M5 11a7 7 0 0 0 14 0M12 18v4" />
          </svg>
        </button>

        {/* Send button — accent bg, white icon */}
        <button
          type="submit"
          disabled={!input.trim() || isStreaming}
          aria-label={COPY.coach.sendButton}
          style={{
            width: 36,
            height: 36,
            borderRadius: 999,
            background: "var(--color-accent)",
            color: "#fff",
            border: "none",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            flexShrink: 0,
            cursor: input.trim() && !isStreaming ? "pointer" : "not-allowed",
            opacity: input.trim() && !isStreaming ? 1 : 0.5,
            padding: 0,
          }}
        >
          {/* Arrow-right send icon — matches mockup */}
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="#fff"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <path d="M5 12h14M13 6l6 6-6 6" />
          </svg>
        </button>
      </form>

      {/* ── Footer disclaimer (.fine) ─────────────────────────────────────── */}
      <p
        style={{
          fontSize: 11.5,
          color: "var(--color-ink-3)",
          textAlign: "center",
          padding: "8px 20px calc(14px + env(safe-area-inset-bottom, 0px))",
          lineHeight: 1.5,
        }}
      >
        Coach uses your wearable, survey &amp; EHR context. General wellness — not
        medical advice.
      </p>
    </div>
  );
}
