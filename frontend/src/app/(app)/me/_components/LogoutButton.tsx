"use client";

/**
 * LogoutButton — client component.
 *
 * Renders as a full-row sign-out button inside the Me screen quick-links list.
 * Accepts optional `className` and `rowStyle` for composability.
 *
 * POSTs /api/auth/logout, then redirects to /login.
 */

import { useState } from "react";
import { useRouter } from "next/navigation";
import { COPY } from "@/lib/copy/copy";

interface LogoutButtonProps {
  /** Additional Tailwind / inline classes applied to the outer button. */
  className?: string;
  /**
   * Inline styles for the button element (e.g. border-top divider).
   * When provided the button renders with an inner row layout matching the
   * other quick-link rows on the Me screen.
   */
  rowStyle?: React.CSSProperties;
}

export default function LogoutButton({
  className,
  rowStyle,
}: LogoutButtonProps) {
  const router = useRouter();
  const [loading, setLoading] = useState(false);

  async function handleLogout() {
    setLoading(true);
    try {
      await fetch("/api/auth/logout", { method: "POST" });
    } finally {
      router.push("/login");
    }
  }

  return (
    <button
      type="button"
      className={className}
      style={rowStyle}
      onClick={handleLogout}
      disabled={loading}
      aria-label={loading ? "Signing out\u2026" : COPY.auth.logout}
    >
      <div className="flex items-center gap-3 px-4 py-3">
        <span className="w-6 text-base shrink-0" aria-hidden="true">
          &#x21AA;
        </span>
        <span
          className="flex-1 text-sm font-medium"
          style={{ color: "var(--color-ink)" }}
        >
          {loading ? "Signing out\u2026" : COPY.auth.logout}
        </span>
        {/* Chevron */}
        <svg
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          aria-hidden="true"
          style={{ color: "var(--color-ink-4)", flexShrink: 0 }}
        >
          <path d="M9 18l6-6-6-6" />
        </svg>
      </div>
    </button>
  );
}
