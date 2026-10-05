import type { Metadata } from "next";
import { FileText } from "lucide-react";
import { redirect } from "next/navigation";
import { connection } from "next/server";
import { googleConfigured } from "@/lib/auth";

export const metadata: Metadata = { title: "Sign in" };

const ERRORS: Record<string, string> = {
  expired: "That sign-in took too long or was opened in another tab. Try again.",
  google: "Google didn't confirm the sign-in. Try again.",
  unverified: "Your Google email address isn't verified yet.",
};

export default async function SignInPage({ searchParams }: { searchParams: Promise<{ error?: string }> }) {
  await connection();
  if (!googleConfigured()) redirect("/");
  const { error } = await searchParams;
  return (
    <main id="main" className="mx-auto flex min-h-dvh max-w-md flex-col justify-center px-4">
      <div className="rounded-[var(--radius-card)] border border-line bg-paper p-8">
        <p className="flex items-center gap-2 font-[family-name:var(--font-heading)] text-[18px] font-semibold">
          <FileText aria-hidden className="size-6 text-primary" /> Job Copilot
        </p>
        <h1 className="mt-6 text-[26px] font-semibold">Sign in to your workspace</h1>
        <p className="mt-2 text-muted">
          Your resumes, jobs and applications stay private to your account. Job Copilot only uses facts you&apos;ve
          confirmed, and never submits an application for you.
        </p>
        {error && (
          <p role="alert" className="mt-4 rounded-[var(--radius-control)] border-l-4 border-blocked/40 bg-blocked-soft p-3 text-[15px]">
            {ERRORS[error] ?? ERRORS.google}
          </p>
        )}
        <a href="/api/auth/signin"
          className="mt-6 flex min-h-11 items-center justify-center rounded-[var(--radius-control)] bg-primary px-4 font-semibold text-on-primary hover:bg-primary-hover">
          Sign in with Google
        </a>
        <p className="mt-4 text-center text-[14px] text-muted">
          <a href="/privacy" className="underline underline-offset-2">How Job Copilot handles your data</a>
        </p>
      </div>
    </main>
  );
}
