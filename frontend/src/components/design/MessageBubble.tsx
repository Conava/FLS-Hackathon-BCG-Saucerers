import * as React from "react";

export interface MessageBubbleProps {
  /** Sender name */
  sender: string;
  /** Message content */
  content: string;
  /** Timestamp string, e.g. "2:34 PM" */
  timestamp?: string;
  /** Whether the message was sent by the current user */
  isOwn?: boolean;
}

/**
 * Care-team message thread bubble.
 * Own messages appear on the right; received messages on the left.
 */
export function MessageBubble({
  sender,
  content,
  timestamp,
  isOwn = false,
}: MessageBubbleProps) {
  return (
    <div
      className={`flex flex-col gap-0.5 max-w-[82%] ${isOwn ? "self-end items-end" : "self-start items-start"}`}
    >
      {!isOwn && (
        <span className="t-caption text-ink-3" style={{ paddingLeft: 2 }}>
          {sender}
        </span>
      )}
      <div
        style={{
          padding: "10px 14px",
          borderRadius: 18,
          fontSize: 13.5,
          lineHeight: 1.5,
          ...(isOwn
            ? {
                background: "var(--color-accent)",
                color: "#fff",
                borderBottomRightRadius: 6,
              }
            : {
                background: "var(--color-surface)",
                border: "1px solid var(--color-border)",
                color: "var(--color-ink)",
                borderBottomLeftRadius: 6,
              }),
        }}
      >
        {content}
      </div>
      {timestamp && (
        <span
          className="t-legal text-ink-4"
          style={{ paddingRight: isOwn ? 2 : 0, paddingLeft: isOwn ? 0 : 2 }}
        >
          {timestamp}
        </span>
      )}
    </div>
  );
}
