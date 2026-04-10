"use client";

import * as React from "react";
import { SuggestedChip } from "@/components/design/Chip";

export interface SuggestedChipsProps {
  /**
   * Array of suggested prompt labels to render as tappable chips.
   */
  suggestions: string[];
  /**
   * Called when the user taps a chip. Passes the chip label as the argument,
   * allowing the parent to pre-fill the chat input.
   */
  onSelect: (label: string) => void;
}

/**
 * Horizontal (wrapping) row of SuggestedChip buttons.
 * Displayed on the coach screen when the thread is empty.
 * Tapping a chip calls `onSelect` with the chip's label.
 */
export function SuggestedChips({ suggestions, onSelect }: SuggestedChipsProps) {
  if (suggestions.length === 0) return null;

  return (
    <div
      style={{
        display: "flex",
        flexWrap: "wrap",
        gap: 8,
        padding: "0 16px 12px",
      }}
      aria-label="Suggested questions"
    >
      {suggestions.map((label) => (
        <SuggestedChip
          key={label}
          label={label}
          onClick={() => onSelect(label)}
        />
      ))}
    </div>
  );
}
