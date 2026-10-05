import type { Metadata, Viewport } from "next";
import { cookies } from "next/headers";
import { connection } from "next/server";
import { Lexend, Source_Sans_3 } from "next/font/google";
import { AppShell } from "@/components/app-shell";
import { SESSION_COOKIE, googleConfigured, readSession } from "@/lib/auth";
import "./globals.css";

const lexend = Lexend({ subsets: ["latin"], weight: ["500", "600", "700"], variable: "--font-lexend" });
const sourceSans = Source_Sans_3({ subsets: ["latin"], weight: ["400", "600"], variable: "--font-source-sans" });

export const metadata: Metadata = {
  title: { default: "Job Copilot", template: "%s · Job Copilot" },
  description: "Truthful tailored resumes, real jobs, and an application tracker. Nothing is invented and nothing is submitted for you.",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#ffffff" },
    { media: "(prefers-color-scheme: dark)", color: "#121b2c" },
  ],
};

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  await connection(); // sign-in is configured at runtime, so pages are never prerendered
  const signInEnabled = googleConfigured();
  const session = signInEnabled ? await readSession((await cookies()).get(SESSION_COOKIE)?.value) : null;
  return (
    <html lang="en" className={`${lexend.variable} ${sourceSans.variable}`}>
      <body className="min-h-dvh antialiased">
        <AppShell signInEnabled={signInEnabled} userName={session?.name ?? null}>
          {children}
        </AppShell>
      </body>
    </html>
  );
}
