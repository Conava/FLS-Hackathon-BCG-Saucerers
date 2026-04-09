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
 * AI bubbles are surface-colored with a teal/violet tint; user bubbles are accent-filled.
 */
export function ChatBubble({ role, content, streaming = false }: ChatBubbleProps) {
  const isAi = role === "ai";

  return (
    <div
      className={cn(
        "max-w-[82%] t-body",
        isAi ? "self-start" : "self-end"
      )}
      style={{
        padding: "10px 14px",
        borderRadius: 18,
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
          style={{ animation: "blink 1s step-end infinite" }}
          aria-hidden="true"
        />
      )}
    </div>
  );
}
