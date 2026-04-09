"use client";

/**
 * LogoutButton — client component.
 *
 * POSTs /api/auth/logout, then redirects to /login.
 */

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { COPY } from "@/lib/copy/copy";

export default function LogoutButton() {
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
    <Button
      variant="outline"
      className="w-full"
      onClick={handleLogout}
      disabled={loading}
    >
      {loading ? "Signing out…" : COPY.auth.logout}
    </Button>
  );
}
