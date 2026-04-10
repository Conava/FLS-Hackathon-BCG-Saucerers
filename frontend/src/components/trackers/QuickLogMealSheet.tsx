"use client";

/**
 * QuickLogMealSheet — manual meal entry bottom sheet.
 *
 * Wraps BottomSheet with a form for entering meal macros without a photo.
 * On submit, calls apiClient.createManualMealLog and notifies the caller.
 *
 * At the top of the sheet there is a "Prefer the camera?" link that navigates
 * to /meal-log (the photo flow) and closes the sheet.
 */

import * as React from "react";
import { useRouter } from "next/navigation";
import { BottomSheet } from "@/components/design/BottomSheet";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { createManualMealLog } from "@/lib/api/client";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface QuickLogMealSheetProps {
  /** Whether the sheet is visible. */
  open: boolean;
  /** Called when the sheet requests open/close. */
  onOpenChange: (open: boolean) => void;
  /** Called after a meal is successfully logged. */
  onSubmitted?: () => void;
}

// ---------------------------------------------------------------------------
// Default form values
// ---------------------------------------------------------------------------

const DEFAULTS = {
  name: "",
  kcal: "",
  protein_g: "0",
  carbs_g: "0",
  fat_g: "0",
  fiber_g: "0",
  notes: "",
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/**
 * Bottom sheet for manually logging a meal without taking a photo.
 *
 * Fields:
 *  - Name (text, required)
 *  - kcal (number, required, 0–3000)
 *  - Protein / Carbs / Fat / Fiber (number, step 1, 0–300, default 0)
 *  - Notes (textarea, optional)
 *
 * Calls `createManualMealLog` on submit. On success invokes `onSubmitted` and
 * closes the sheet.
 */
export function QuickLogMealSheet({
  open,
  onOpenChange,
  onSubmitted,
}: QuickLogMealSheetProps) {
  const router = useRouter();

  const [fields, setFields] = React.useState(DEFAULTS);
  const [saving, setSaving] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  /** Reset form state whenever the sheet opens. */
  React.useEffect(() => {
    if (open) {
      setFields(DEFAULTS);
      setError(null);
      setSaving(false);
    }
  }, [open]);

  function handleClose() {
    onOpenChange(false);
  }

  function handleCameraLink() {
    router.push("/meal-log");
    handleClose();
  }

  function handleChange(
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>,
  ) {
    const { name, value } = e.target;
    setFields((prev) => ({ ...prev, [name]: value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSaving(true);

    try {
      await createManualMealLog({
        name: fields.name.trim(),
        kcal: Number(fields.kcal),
        protein_g: Number(fields.protein_g),
        carbs_g: Number(fields.carbs_g),
        fat_g: Number(fields.fat_g),
        fiber_g: Number(fields.fiber_g),
        notes: fields.notes.trim() || undefined,
      });

      onSubmitted?.();
      handleClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save meal.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <BottomSheet open={open} onClose={handleClose} title="Log a meal">
      {/* Camera shortcut */}
      <button
        type="button"
        onClick={handleCameraLink}
        style={{
          background: "none",
          border: "none",
          padding: 0,
          marginBottom: 16,
          fontSize: 13,
          color: "var(--color-accent)",
          cursor: "pointer",
          textDecoration: "underline",
        }}
      >
        Prefer the camera? Use meal vision instead
      </button>

      <form onSubmit={handleSubmit} noValidate style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        {/* Name */}
        <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          <Label htmlFor="qlm-name">Name</Label>
          <Input
            id="qlm-name"
            name="name"
            type="text"
            value={fields.name}
            onChange={handleChange}
            placeholder="e.g. Oat porridge"
            required
            autoComplete="off"
          />
        </div>

        {/* kcal */}
        <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          <Label htmlFor="qlm-kcal">kcal</Label>
          <Input
            id="qlm-kcal"
            name="kcal"
            type="number"
            value={fields.kcal}
            onChange={handleChange}
            placeholder="0"
            required
            min={0}
            max={3000}
            step={1}
          />
        </div>

        {/* Macro row: Protein + Carbs */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <Label htmlFor="qlm-protein">Protein g</Label>
            <Input
              id="qlm-protein"
              name="protein_g"
              type="number"
              value={fields.protein_g}
              onChange={handleChange}
              min={0}
              max={300}
              step={1}
            />
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <Label htmlFor="qlm-carbs">Carbs g</Label>
            <Input
              id="qlm-carbs"
              name="carbs_g"
              type="number"
              value={fields.carbs_g}
              onChange={handleChange}
              min={0}
              max={300}
              step={1}
            />
          </div>
        </div>

        {/* Macro row: Fat + Fiber */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <Label htmlFor="qlm-fat">Fat g</Label>
            <Input
              id="qlm-fat"
              name="fat_g"
              type="number"
              value={fields.fat_g}
              onChange={handleChange}
              min={0}
              max={300}
              step={1}
            />
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <Label htmlFor="qlm-fiber">Fiber g</Label>
            <Input
              id="qlm-fiber"
              name="fiber_g"
              type="number"
              value={fields.fiber_g}
              onChange={handleChange}
              min={0}
              max={300}
              step={1}
            />
          </div>
        </div>

        {/* Notes */}
        <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          <Label htmlFor="qlm-notes">Notes</Label>
          <Textarea
            id="qlm-notes"
            name="notes"
            value={fields.notes}
            onChange={handleChange}
            placeholder="Optional notes…"
            rows={2}
          />
        </div>

        {/* Error */}
        {error && (
          <p
            role="alert"
            style={{ margin: 0, fontSize: 13, color: "var(--color-danger, #d32f2f)" }}
          >
            {error}
          </p>
        )}

        {/* Submit */}
        <Button
          type="submit"
          disabled={saving || !fields.name.trim() || !fields.kcal}
          style={{ marginTop: 4 }}
        >
          {saving ? "Saving…" : "Save"}
        </Button>
      </form>
    </BottomSheet>
  );
}
