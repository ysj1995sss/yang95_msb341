// A mistyped or old link lands here instead of Next's bare "404 | This page could not be found."
// (dogfood round 5).
import type { Metadata } from "next";
import { LinkButton, PageHeader } from "@/components/ui";

export const metadata: Metadata = { title: "Page not found" };

export default function NotFound() {
  return (
    <div className="mx-auto max-w-xl py-10">
      <PageHeader title="Page not found" description="This link doesn't lead to a page in Job Copilot. Your data is safe." />
      <div className="flex flex-wrap gap-2">
        <LinkButton href="/" variant="primary">Go to Home</LinkButton>
        <LinkButton href="/jobs">Find jobs</LinkButton>
      </div>
    </div>
  );
}
