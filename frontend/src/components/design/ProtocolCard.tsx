"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

export interface ProtocolCardProps {
  /** Protocol action title */
  action: string;
  /** Optional rationale / supporting text */
  rationale?: string;
  /** Category tag, e.g. "Nutrition" */
  category?: string;
  /** Whether the action is completed */
  done: boolean;
  /** Called when the user taps the check button */
  onToggle: () => void;
}

/**
 * Checklist item for the Today protocol.
 * Tap the check button to toggle the `done` state.
 */
export function ProtocolCard({
  action,
  rationale,
  category,
  done,
  onToggle,
}: ProtocolCardProps) {
  return (
    <li
      className="flex items-start gap-3 bg-surface rounded-[14px] list-none"
      style={{
        padding: "12px 14px",
        border: "1px solid var(--color-border)",
      }}
    >
      {/* Check button */}
      <button
        type="button"
        onClick={onToggle}
        aria-label={done ? "Mark as incomplete" : "Mark as complete"}
        aria-pressed={done}
        className={cn(
          "flex-shrink-0 flex items-center justify-center rounded-full transition-colors duration-180",
          done
            ? "bg-good border-good"
            : "bg-transparent border-border-2"
        )}
        style={{
          width: 26,
          height: 26,
          border: done
            ? "2px solid var(--color-good)"
            : "2px solid var(--color-border-2)",
        }}
      >
        {done && (
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="white"
            strokeWidth="3"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <path d="M5 12 10 17 19 7" />
          </svg>
        )}
      </button>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <p
          className={cn(
            "t-body-strong",
            done && "line-through text-ink-3"
          )}
        >
          {action}
        </p>
        {rationale && (
          <p className="t-caption text-ink-3" style={{ marginTop: 2 }}>
            {rationale}
          </p>
        )}
        {category && (
          <p
            className="uppercase font-bold text-accent"
            style={{
              fontSize: 10,
              letterSpacing: "0.05em",
              marginTop: 4,
            }}
          >
            {category}
          </p>
        )}
      </div>
    </li>
  );
}
