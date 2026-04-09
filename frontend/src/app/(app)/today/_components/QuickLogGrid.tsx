"use client";

import * as React from "react";
import Link from "next/link";

interface QuickLogItem {
  emoji: string;
  label: string;
  href?: string;
}

const ITEMS: QuickLogItem[] = [
  { emoji: "🍽️", label: "Meal", href: "/meal-log" },
  { emoji: "😴", label: "Sleep" },
  { emoji: "🏃", label: "Workout" },
  { emoji: "💧", label: "Water" },
];

/**
 * 4-column quick-log grid for the Today screen.
 * Each button opens the relevant logging flow.
 * Meal button links directly to /meal-log.
 */
export function QuickLogGrid() {
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(4, 1fr)",
        gap: 8,
      }}
    >
      {ITEMS.map(({ emoji, label, href }) => {
        const inner = (
          <>
            <span style={{ fontSize: 20 }} aria-hidden="true">
              {emoji}
            </span>
            <span
              style={{
                fontSize: 10.5,
                fontWeight: 600,
                marginTop: 4,
                color: "var(--color-ink)",
              }}
            >
              {label}
            </span>
          </>
        );

        if (href) {
          return (
            <Link
              key={label}
              href={href}
              aria-label={label}
              className="card"
              style={{
                padding: "12px 6px",
                textAlign: "center",
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                textDecoration: "none",
                boxShadow: "none",
              }}
            >
              {inner}
            </Link>
          );
        }

        return (
          <button
            key={label}
            type="button"
            aria-label={label}
            className="card"
            style={{
              padding: "12px 6px",
              textAlign: "center",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              cursor: "pointer",
              border: "1px solid var(--color-border)",
              background: "var(--color-surface)",
              boxShadow: "none",
              width: "100%",
            }}
          >
            {inner}
          </button>
        );
      })}
    </div>
  );
}
