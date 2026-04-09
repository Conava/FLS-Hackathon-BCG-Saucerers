import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import ServiceWorkerRegister from "@/components/pwa/ServiceWorkerRegister";

/**
 * Load Inter with the full weight range used across the design system
 * (300 thin → 800 extrabold). next/font/google handles self-hosting and
 * zero layout-shift automatically.
 */
const inter = Inter({
  subsets: ["latin"],
  weight: ["300", "400", "500", "600", "700", "800"],
  variable: "--font-sans",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Longevity",
  description: "AI-driven longevity companion",
  manifest: "/manifest.webmanifest",
};

/**
 * Viewport settings:
 * - viewport-fit=cover lets the app paint behind the notch / home indicator.
 * - maximumScale=1 prevents iOS auto-zoom on input focus (accessibility
 *   trade-off accepted for this mobile-first UI).
 * - themeColor matches --color-bg (#F7F6F3) so the browser chrome blends in.
 */
export const viewport: Viewport = {
  themeColor: "#F7F6F3",
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  viewportFit: "cover",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={inter.variable}>
      {/* inter.variable injects --font-sans into the document root so
          globals.css can reference it via var(--font-sans). */}
      <body className={inter.className}>
        {children}
        <ServiceWorkerRegister />
      </body>
    </html>
  );
}
