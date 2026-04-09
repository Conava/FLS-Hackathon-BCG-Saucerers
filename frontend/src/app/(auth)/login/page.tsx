"use client";

/**
 * Demo Login Screen
 *
 * Single patient ID input + demo shortcuts.
 * POSTs to /api/auth/login on submit; on success redirects to /today.
 * No passwords — this is a demo-gate only.
 */

import { useState } from "react";
import { useRouter } from "next/navigation";
import { COPY } from "@/lib/copy/copy";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

/** Demo accounts shown as quick-fill shortcuts below the form. */
const DEMO_PATIENTS: { label: string; patientId: string }[] = [
  { label: "Rebecca (PT0199)", patientId: "PT0199" },
  { label: "PT0282", patientId: "PT0282" },
  { label: "PT0001", patientId: "PT0001" },
];

/**
 * LoginPage — centered card on sand background.
 * Client component so we can manage form state and call the API route.
 */
export default function LoginPage() {
  const router = useRouter();
  const [patientId, setPatientId] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);

    const trimmed = patientId.trim();
    if (!trimmed) {
      setError("Please enter a Patient ID.");
      return;
    }

    setLoading(true);
    try {
      const res = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ patient_id: trimmed }),
      });

      if (!res.ok) {
        const data = (await res.json()) as { error?: string };
        setError(
          data.error ?? COPY.errors.generic,
        );
        return;
      }

      router.push("/today");
    } catch {
      setError(COPY.errors.network);
    } finally {
      setLoading(false);
    }
  }

  function handleDemoClick(id: string) {
    setPatientId(id);
    setError(null);
  }

  return (
    <main
      className="flex min-h-dvh flex-col items-center justify-center px-4 py-12"
      style={{ backgroundColor: "var(--color-bg)" }}
    >
      {/* Brand mark */}
      <div className="mb-8 text-center">
        <span
          className="text-2xl font-extrabold tracking-tight"
          style={{ color: "var(--color-accent)" }}
        >
          {COPY.app.title}
        </span>
        <p
          className="mt-1 text-sm"
          style={{ color: "var(--color-ink-3)" }}
        >
          {COPY.app.tagline}
        </p>
      </div>

      <Card
        className="w-full max-w-sm"
        style={{
          boxShadow: "var(--shadow-md)",
          borderColor: "var(--color-border)",
          backgroundColor: "var(--color-surface)",
        }}
      >
        <CardHeader className="pb-4">
          <CardTitle>
            <h1
              className="text-[22px] font-bold"
              style={{ color: "var(--color-ink)" }}
            >
              {COPY.auth.login.heading}
            </h1>
          </CardTitle>
          <CardDescription style={{ color: "var(--color-ink-3)" }}>
            {COPY.auth.login.subheading}
          </CardDescription>
        </CardHeader>

        <CardContent>
          <form onSubmit={handleSubmit} noValidate className="space-y-4">
            <div className="space-y-1.5">
              <label
                htmlFor="patient-id"
                className="text-sm font-medium"
                style={{ color: "var(--color-ink-2)" }}
              >
                Patient ID
              </label>
              <Input
                id="patient-id"
                type="text"
                placeholder="pt-001 or PT0199"
                value={patientId}
                onChange={(e) => {
                  setPatientId(e.target.value);
                  setError(null);
                }}
                autoComplete="off"
                autoCapitalize="none"
                spellCheck={false}
                aria-describedby={error ? "login-error" : undefined}
                style={{
                  borderColor: error
                    ? "var(--color-danger)"
                    : "var(--color-border-2)",
                }}
              />
            </div>

            {error && (
              <p
                id="login-error"
                role="alert"
                className="text-sm"
                style={{ color: "var(--color-danger)" }}
              >
                {error}
              </p>
            )}

            <Button
              type="submit"
              disabled={loading}
              className="w-full font-semibold"
              style={{
                backgroundColor: "var(--color-accent)",
                color: "#ffffff",
              }}
            >
              {loading ? "Signing in…" : COPY.auth.login.cta}
            </Button>
          </form>

          {/* Demo shortcuts */}
          <div className="mt-6">
            <p
              className="mb-2 text-xs font-medium uppercase tracking-wider"
              style={{ color: "var(--color-ink-4)" }}
            >
              Demo accounts
            </p>
            <div className="flex flex-wrap gap-2">
              {DEMO_PATIENTS.map(({ label, patientId: id }) => (
                <button
                  key={id}
                  type="button"
                  data-demo="true"
                  onClick={() => handleDemoClick(id)}
                  className="rounded-full px-3 py-1 text-xs font-medium transition-colors"
                  style={{
                    backgroundColor: "var(--color-accent-lt)",
                    color: "var(--color-accent)",
                    border: "1px solid var(--color-accent-md)",
                  }}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* AI disclosure required on auth screens */}
      <p
        className="mt-6 max-w-sm text-center text-xs"
        style={{ color: "var(--color-ink-4)" }}
      >
        {COPY.coach.disclosure}
      </p>
    </main>
  );
}
