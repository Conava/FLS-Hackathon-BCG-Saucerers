"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

export interface PillarCardProps {
  /** Pillar title, e.g. "Clinics" */
  title: string;
  /** Supporting description */
  description?: string;
  /** Icon element */
  icon?: React.ReactNode;
  /** Whether this pillar is currently selected */
  active?: boolean;
  /** Called on tap */
  onClick?: () => void;
}

/**
 * Care tab pillar card (Clinics / Diagnostics / Home Care).
 */
export function PillarCard({
  title,
  description,
  icon,
  active = false,
  onClick,
}: PillarCardProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "flex flex-col items-start gap-2 w-full text-left transition-all",
        active
          ? "bg-accent-lt border-accent-md"
          : "bg-surface border-border hover:shadow-app-sm"
      )}
      style={{
        padding: 16,
        borderRadius: 14,
        border: `1px solid ${active ? "var(--color-accent-md)" : "var(--color-border)"}`,
      }}
      aria-pressed={active}
    >
      {icon && (
        <div
          className="flex items-center justify-center rounded-[10px]"
          style={{
            width: 40,
            height: 40,
            background: active
              ? "var(--color-accent)"
              : "var(--color-bg-2)",
            color: active ? "#fff" : "var(--color-accent)",
          }}
          aria-hidden="true"
        >
          {icon}
        </div>
      )}
      <div>
        <p
          className="t-body-strong"
          style={{ color: active ? "var(--color-accent-2)" : "var(--color-ink)" }}
        >
          {title}
        </p>
        {description && (
          <p className="t-caption text-ink-3" style={{ marginTop: 2 }}>
            {description}
          </p>
        )}
      </div>
    </button>
  );
}
