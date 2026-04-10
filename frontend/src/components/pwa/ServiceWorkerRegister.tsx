"use client";

import { useEffect } from "react";

/**
 * ServiceWorkerRegister
 *
 * Mounts once in the root layout and registers `/sw.js` on the first render.
 * Registration is intentionally **production-only** — in development the SW
 * would interfere with HMR and Next.js fast-refresh.
 *
 * Renders null; this component exists purely for its side-effect.
 */
export default function ServiceWorkerRegister() {
  useEffect(() => {
    if (
      process.env.NODE_ENV === "production" &&
      typeof navigator !== "undefined" &&
      "serviceWorker" in navigator
    ) {
      navigator.serviceWorker
        .register("/sw.js")
        .catch((err) => console.error("[SW] Registration failed:", err));
    }
  }, []);

  return null;
}
