"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

export interface ChatBubbleProps {
  /** Message role — determines visual style */
  role: "ai" | "user";
  /** Message content */
  content: string;
  /**
   * When true on the last AI bubble, shows a blinking cursor
   * to indicate streaming in progress.
   */
  streaming?: boolean;
}

/**
 * Chat message bubble for the AI Coach screen.
 *
 * Matches mockup `.msg` / `.msg.ai` / `.msg.me` styles:
 * - max-width 82%, padding 10px 14px, border-radius 18px, font-size 13.5px, line-height 1.5
 * - AI: surface bg, 1px border, border-bottom-left-radius 6px, align-self flex-start
 * - User: accent bg, white text, border-bottom-right-radius 6px, align-self flex-end
 * - Streaming AI bubble appends a blinking cursor span.
 */
export function ChatBubble({ role, content, streaming = false }: ChatBubbleProps) {
  const isAi = role === "ai";

  return (
    <>
      <div
        className={cn("max-w-[82%]", isAi ? "self-start" : "self-end")}
        style={{
          padding: "10px 14px",
          borderRadius: 18,
          fontSize: 13.5,
          lineHeight: 1.5,
          ...(isAi
            ? {
                background: "var(--color-surface)",
                border: "1px solid var(--color-border)",
                color: "var(--color-ink)",
                borderBottomLeftRadius: 6,
              }
            : {
                background: "var(--color-accent)",
                color: "#fff",
                borderBottomRightRadius: 6,
              }),
        }}
      >
        {content}
        {streaming && isAi && (
          <span
            className="inline-block w-0.5 h-3.5 bg-current align-middle ml-0.5"
            style={{ animation: "chat-blink 1s step-end infinite" }}
            aria-hidden="true"
          />
        )}
      </div>
      {streaming && isAi && (
        <style>{`
          @keyframes chat-blink {
            0%, 100% { opacity: 1; }
            50% { opacity: 0; }
          }
        `}</style>
      )}
    </>
  );
}
