import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Longevity",
  description: "AI-driven longevity companion",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
