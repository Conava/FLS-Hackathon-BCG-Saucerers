"use client";

/**
 * GdprActions — client component for GDPR Export and Delete buttons.
 *
 * Export: calls getGDPRExport(), triggers a JSON blob download.
 * Delete: opens a confirmation dialog, calls requestGDPRDelete(),
 *         then POSTs /api/auth/logout and redirects to /login.
 *
 * Stack: Next.js 15 App Router, React 19.
 */

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { COPY } from "@/lib/copy/copy";
import { getGDPRExport, requestGDPRDelete } from "@/lib/api/client";

export default function GdprActions() {
  const router = useRouter();
  const [exportLoading, setExportLoading] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deleteLoading, setDeleteLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  /** Download the GDPR data export as a JSON file. */
  async function handleExport() {
    setError(null);
    setExportLoading(true);
    try {
      const data = await getGDPRExport();
      const blob = new Blob([JSON.stringify(data, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `longevity-export-${data.patient_id}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch {
      setError(COPY.errors.generic);
    } finally {
      setExportLoading(false);
    }
  }

  /** Confirm GDPR deletion: delete account, logout, redirect to /login. */
  async function handleConfirmDelete() {
    setError(null);
    setDeleteLoading(true);
    try {
      await requestGDPRDelete();
      // Clear the session cookie
      await fetch("/api/auth/logout", { method: "POST" });
      router.push("/login");
    } catch {
      setError(COPY.errors.generic);
      setDeleteLoading(false);
      setDeleteOpen(false);
    }
  }

  return (
    <div className="space-y-3">
      <p
        className="text-sm"
        style={{ color: "var(--color-ink-3)" }}
      >
        {COPY.me.gdpr.body}
      </p>

      {error && (
        <p
          role="alert"
          className="text-sm"
          style={{ color: "var(--color-danger)" }}
        >
          {error}
        </p>
      )}

      {/* Export */}
      <Button
        variant="outline"
        className="w-full"
        onClick={handleExport}
        disabled={exportLoading}
        aria-label={exportLoading ? "Exporting…" : COPY.me.gdpr.exportData}
      >
        {exportLoading ? "Exporting…" : COPY.me.gdpr.exportData}
      </Button>

      {/* Delete */}
      <Button
        variant="destructive"
        className="w-full"
        onClick={() => setDeleteOpen(true)}
        aria-label={COPY.me.gdpr.deleteAccount}
      >
        {COPY.me.gdpr.deleteAccount}
      </Button>

      {/* Confirmation dialog */}
      <Dialog open={deleteOpen} onOpenChange={setDeleteOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{COPY.me.gdpr.heading}</DialogTitle>
            <DialogDescription>
              {COPY.me.gdpr.confirmDelete}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setDeleteOpen(false)}
              disabled={deleteLoading}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleConfirmDelete}
              disabled={deleteLoading}
              aria-label="Confirm Delete"
            >
              {deleteLoading ? "Deleting…" : "Confirm Delete"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
