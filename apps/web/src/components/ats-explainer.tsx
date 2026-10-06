import { Info } from "lucide-react";
import type { AtsExplainerText } from "@/lib/types";

/** What Job Copilot's ATS checks are and aren't (spec 010). The text comes from the API. */
export function AtsExplainer({ explainer }: { explainer: AtsExplainerText }) {
  return (
    <details className="mt-4 rounded-[var(--radius-card)] border border-line bg-paper p-3 text-[15px]">
      <summary className="flex cursor-pointer items-center gap-2 font-semibold"><Info aria-hidden className="size-4 text-primary" /> {explainer.title}</summary>
      <div className="mt-2 flex flex-col gap-2 text-muted">{explainer.paragraphs.map((p) => <p key={p}>{p}</p>)}</div>
    </details>
  );
}
