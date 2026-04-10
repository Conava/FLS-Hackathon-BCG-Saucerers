import * as React from "react";

/**
 * Three-dot animated typing indicator shown while the AI is composing a response.
 * Dots bounce with staggered delays (0ms, 150ms, 300ms).
 */
export function TypingIndicator() {
  const dots = [0, 150, 300];

  return (
    <div
      className="self-start flex items-center gap-1"
      style={{
        padding: "10px 14px",
        borderRadius: 18,
        borderBottomLeftRadius: 6,
        background: "var(--color-surface)",
        border: "1px solid var(--color-border)",
      }}
      aria-label="AI is typing"
      role="status"
    >
      {dots.map((delay, i) => (
        <span
          key={i}
          className="rounded-full"
          style={{
            width: 6,
            height: 6,
            background: "var(--color-ink-3)",
            display: "inline-block",
            animation: `typing-bounce 1.2s ease infinite`,
            animationDelay: `${delay}ms`,
          }}
          aria-hidden="true"
        />
      ))}

      <style>{`
        @keyframes typing-bounce {
          0%, 60%, 100% { transform: translateY(0); opacity: 0.4; }
          30% { transform: translateY(-4px); opacity: 1; }
        }
      `}</style>
    </div>
  );
}
