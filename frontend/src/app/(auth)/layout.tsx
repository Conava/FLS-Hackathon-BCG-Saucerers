import type { ReactNode } from "react";

/**
 * Auth shell for login and onboarding.
 * No tab bar — provides a minimal centered layout.
 */
export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div
      style={{
        minHeight: "100dvh",
        display: "flex",
        flexDirection: "column",
      }}
    >
      {children}
    </div>
  );
}
