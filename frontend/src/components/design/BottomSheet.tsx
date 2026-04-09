"use client";

import * as React from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { cn } from "@/lib/utils";

export interface BottomSheetProps {
  /** Whether the sheet is visible */
  open: boolean;
  /** Called when the sheet requests close (scrim tap or Escape) */
  onClose: () => void;
  /** Optional sheet title */
  title?: string;
  /** Sheet content */
  children: React.ReactNode;
  /** Additional class names for the inner sheet panel */
  className?: string;
}

/**
 * Modal sheet that slides up from the bottom of the screen.
 * Wraps Radix Dialog — overlay (scrim) tap or Escape key dismisses it.
 */
export function BottomSheet({
  open,
  onClose,
  title,
  children,
  className,
}: BottomSheetProps) {
  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent
        className={cn(
          // Override the default centered Dialog positioning to bottom-sheet
          "fixed bottom-0 left-0 right-0 top-auto translate-x-0 translate-y-0",
          "w-full max-w-none overflow-y-auto",
          "rounded-t-[24px] rounded-b-none",
          "px-5 pb-7 pt-5",
          // Remove the default top-center transform
          "data-[state=open]:slide-in-from-bottom data-[state=closed]:slide-out-to-bottom",
          className
        )}
        style={{ maxHeight: "85%" }}
        aria-labelledby={title ? "bottom-sheet-title" : undefined}
      >
        {/* Drag handle */}
        <div className="flex justify-center" style={{ marginBottom: 14 }}>
          <div
            className="rounded-full"
            style={{
              width: 44,
              height: 4,
              background: "var(--color-border-2)",
            }}
            aria-hidden="true"
          />
        </div>

        {title ? (
          <DialogHeader>
            <DialogTitle
              id="bottom-sheet-title"
              className="t-h2 text-ink text-left"
            >
              {title}
            </DialogTitle>
          </DialogHeader>
        ) : (
          /* Visually-hidden title required by Radix Dialog for a11y */
          <DialogTitle className="sr-only">Panel</DialogTitle>
        )}

        {children}
      </DialogContent>
    </Dialog>
  );
}
