"use client";

import * as React from "react";
import * as DialogPrimitive from "@radix-ui/react-dialog";
import { cn } from "@/lib/utils";

export interface BottomSheetProps {
  /** Whether the sheet is visible */
  open: boolean;
  /** Called when the sheet requests close (scrim tap, swipe-down, or Escape) */
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
 *
 * Design decisions:
 * - Uses Radix Dialog primitives directly (NOT the shared DialogContent) so we
 *   can replace the dark `bg-black/80` overlay with a fully transparent one.
 *   The transparent overlay still captures pointer events, giving us
 *   click-outside-to-close without dimming the page.
 * - The panel itself is fully opaque: `var(--color-surface)` (#FFF), 1 px
 *   border, and a strong drop-shadow so it floats over the content below.
 * - Safe-area-inset-bottom is added to the bottom padding so the sheet
 *   respects the iPhone home indicator.
 * - Max height is 85 dvh with overflow-y:auto for tall content.
 */
export function BottomSheet({
  open,
  onClose,
  title,
  children,
  className,
}: BottomSheetProps) {
  return (
    <DialogPrimitive.Root open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogPrimitive.Portal>
        {/*
         * Invisible overlay — still fills the viewport and receives pointer
         * events so clicking outside the sheet dismisses it, but has zero
         * visual impact on the page behind.
         */}
        <DialogPrimitive.Overlay
          className="fixed inset-0 z-50"
          style={{ background: "transparent" }}
        />

        {/* Sheet panel */}
        <DialogPrimitive.Content
          aria-labelledby={title ? "bottom-sheet-title" : undefined}
          className={cn(
            "fixed bottom-0 left-0 right-0 z-50",
            "w-full overflow-y-auto",
            "rounded-t-[24px] rounded-b-none",
            "px-5 pt-5",
            className
          )}
          style={{
            maxHeight: "85dvh",
            background: "#FFFFFF",
            backgroundColor: "#FFFFFF",
            opacity: 1,
            border: "1px solid var(--color-border)",
            boxShadow: "0 -8px 32px rgba(14, 23, 38, 0.18)",
            paddingBottom: "calc(1.75rem + env(safe-area-inset-bottom))",
          }}
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
            <DialogPrimitive.Title
              id="bottom-sheet-title"
              className="t-h2 text-ink text-left"
            >
              {title}
            </DialogPrimitive.Title>
          ) : (
            /* Visually-hidden title required by Radix Dialog for a11y.
               Uses sr-only utility class to keep the title accessible
               without a visual footprint. */
            <DialogPrimitive.Title className="sr-only">
              Panel
            </DialogPrimitive.Title>
          )}

          {children}
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}
