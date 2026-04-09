"use client";

import * as React from "react";
import * as DialogPrimitive from "@radix-ui/react-dialog";
import { DialogHeader, DialogTitle } from "@/components/ui/dialog";
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
          className="fixed inset-0 z-50 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0"
          style={{ background: "transparent" }}
        />

        {/* Sheet panel */}
        <DialogPrimitive.Content
          aria-labelledby={title ? "bottom-sheet-title" : undefined}
          className={cn(
            // Position: anchored to the bottom edge
            "fixed bottom-0 left-0 right-0 z-50",
            // Size
            "w-full overflow-y-auto",
            // Shape
            "rounded-t-[24px] rounded-b-none",
            // Spacing — extra bottom padding for safe-area (home indicator)
            "px-5 pt-5",
            // Animation (slide up/down)
            "duration-300 ease-out",
            "data-[state=open]:animate-in data-[state=closed]:animate-out",
            "data-[state=open]:slide-in-from-bottom-full data-[state=closed]:slide-out-to-bottom-full",
            className
          )}
          style={{
            maxHeight: "85dvh",
            // Solid opaque surface — never transparent
            background: "var(--color-surface)",
            border: "1px solid var(--color-border)",
            boxShadow: "var(--shadow-lg)",
            // Respect iPhone home-indicator notch
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
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}
