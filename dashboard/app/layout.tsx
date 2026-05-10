import "./globals.css";
import type { Metadata } from "next";
import { Space_Grotesk, Spectral } from "next/font/google";

const display = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-display"
});

const body = Spectral({
  subsets: ["latin"],
  variable: "--font-body",
  weight: ["400", "500", "600"]
});

export const metadata: Metadata = {
  title: "Hawk Eye Dashboard",
  description: "AI-powered surveillance dashboard with real-time detection and alerts"
};

export default function RootLayout({
  children
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${display.variable} ${body.variable}`}>
      <body className="bg-ink text-fog font-body antialiased">
        {children}
      </body>
    </html>
  );
}
