import type { ResumeSourceInfo } from "@/lib/types";

export function ResumeSource({ info }: { info?: ResumeSourceInfo | null }) {
  if (!info) return <p className="mt-3 text-[14px] text-muted">Source details unavailable for this older review.</p>;
  return (
    <div className="my-4 rounded-[var(--radius-control)] border border-line p-3 text-[14px]">
      <dl className="grid gap-2 sm:grid-cols-[100px_1fr]">
        <dt className="font-semibold">Resume file</dt><dd className="break-words">{info.file_label}</dd>
        <dt className="font-semibold">Facts</dt><dd>{info.facts_label}</dd>
      </dl>
      <p className="mt-2 text-muted">{info.note}</p>
    </div>
  );
}
