import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Haki Systems — AI Prospecting Platform",
  description: "AI-powered prospecting and outreach for Haki Systems.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
