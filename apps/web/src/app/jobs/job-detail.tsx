"use client";

import { Check, CircleAlert, ExternalLink, Minus, X } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Alert, Button, Chip, ErrorBox, LinkButton, Spinner, toneOf, useToast } from "@/components/ui";
import { api, useResource } from "@/lib/api";
import type { Evidence, JobDetail as Detail } from "@/lib/types";

const MARKS = {
  strong: { icon: Check, className: "bg-verified-soft text-verified", label: "Strong match" },
  partial: { icon: CircleAlert, className: "bg-review-soft text-review", label: "Partial match" },
  missing: { icon: X, className: "bg-blocked-soft text-blocked", label: "Missing" },
  unknown: { icon: Minus, className: "bg-canvas text-muted", label: "Unknown" },
} as const;

function EvidenceList({ kind, items }: { kind: keyof typeof MARKS; items: Array<Evidence | string> }) {
  const mark = MARKS[kind];
  const Icon = mark.icon;
  return (
    <ul className="flex flex-col gap-2">
      {items.map((item) => {
        const text = typeof item === "string" ? item : item.requirement;
        return (
          <li key={text} className="flex gap-3">
            <span className={`mt-0.5 flex size-6 shrink-0 items-center justify-center rounded-full ${mark.className}`}>
              <Icon aria-hidden className="size-4" />
              <span className="sr-only">{mark.label}:</span>
            </span>
            <span>
              <span className="font-semibold">{text}</span>
              {typeof item !== "string" && item.evidence && <span className="text-muted"> — {item.evidence}</span>}
            </span>
          </li>
        );
      })}
    </ul>
  );
}

export function JobDetailPanel({ jobId, onChanged }: { jobId: string; onChanged: () => void }) {
  const router = useRouter();
  const toast = useToast();
  const { data, error, loading, reload } = useResource<Detail>(`/jobs/${encodeURIComponent(jobId)}`);
  const [busy, setBusy] = useState<string | null>(null);

  async function act(action: "save" | "pass" | "apply") {
    setBusy(action);
    try {
      const result = await api<{ next?: string }>(`/jobs/${encodeURIComponent(jobId)}/action`, { method: "POST", json: { action } });
      if (result.next) {
        router.push(result.next);
        return;
      }
      toast(action === "save" ? "Saved. Find it under Saved." : "Passed.");
      onChanged();
      reload();
    } catch (e) {
      toast((e as Error).message);
    } finally {
      setBusy(null);
    }
  }

  if (error) return <ErrorBox error={error} retry={reload} />;
  if (loading && !data) return <Spinner label="Loading the posting" />;
  if (!data) return null;
  const { row } = data;
  const meta = [row.company, row.location, row.work_mode === "Work mode not stated" ? "" : row.work_mode, row.freshness]
    .filter(Boolean).join(" · ");

  return (
    <article aria-labelledby="job-title" className="flex flex-col gap-6">
      <header>
        <h2 id="job-title" className="text-[24px] leading-tight font-semibold">{row.title}</h2>
        <p className="mt-1 text-muted">{meta}</p>
        <div className="mt-3 flex flex-wrap gap-2">
          <Chip tone={toneOf(row.fit_tone)}>{`Candidate fit ${row.fit.replace("Fit ", "")}`}</Chip>
          <Chip tone={toneOf(row.quality_tone)}>{`Posting ${row.quality.toLowerCase()}`}</Chip>
          <Chip>{row.salary}</Chip>
          <Chip tone={row.is_demo ? "review" : "neutral"}>{row.source}</Chip>
          {row.status !== "New" && <Chip tone="primary">{row.status}</Chip>}
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          <Button variant="primary" busy={busy === "apply"} disabled={row.is_demo} onClick={() => act("apply")}
            title="Opens Tailor with this job loaded. Nothing is submitted.">
            Prepare this application
          </Button>
          <Button busy={busy === "save"} onClick={() => act("save")}>Save</Button>
          <Button busy={busy === "pass"} onClick={() => act("pass")}>Pass</Button>
        </div>
      </header>

      {data.hard_gates.length > 0 && (
        <section aria-labelledby="gates" className="flex flex-col gap-2">
          <h3 id="gates" className="text-[17px] font-semibold">Check before proceeding</h3>
          {data.hard_gates.map((g) => <Alert key={g} tone="blocked">{g}</Alert>)}
        </section>
      )}

      <section aria-labelledby="fit" className="flex flex-col gap-4">
        <div>
          <h3 id="fit" className="text-[17px] font-semibold">Why this role may fit you</h3>
          <p className="text-muted">{data.summary}</p>
        </div>
        {data.strong.length > 0 && <div><h4 className="mb-2 text-[14px] font-semibold text-muted uppercase">Strong matches</h4><EvidenceList kind="strong" items={data.strong} /></div>}
        {data.partial.length > 0 && <div><h4 className="mb-2 text-[14px] font-semibold text-muted uppercase">Partial matches</h4><EvidenceList kind="partial" items={data.partial} /></div>}
        {!data.strong.length && !data.partial.length && <p className="text-muted">No matching evidence found in your verified facts yet.</p>}
        <div>
          <h4 className="mb-2 text-[14px] font-semibold text-muted uppercase">Missing from your background</h4>
          {data.gaps.length > 0 ? <EvidenceList kind="missing" items={data.gaps} />
            : <p className="text-muted">{data.fit_measured ? "Nothing genuinely missing against the stated requirements." : "Not known yet: this needs your Career Profile to compare against."}</p>}
        </div>
        {data.unknowns.length > 0 && <div><h4 className="mb-2 text-[14px] font-semibold text-muted uppercase">Important unknowns</h4><EvidenceList kind="unknown" items={data.unknowns} /></div>}
        <p className="text-[14px] text-muted">Missing items are never added to your resume. Candidate fit measures your background, not how well a resume shows it.</p>
      </section>

      <section aria-labelledby="keywords">
        <h3 id="keywords" className="text-[17px] font-semibold">Key requirements and keywords</h3>
        {data.keywords ? (
          <>
            <p className="text-muted">{data.keywords.summary}</p>
            {data.keywords.missing.length > 0 && (
              <div className="mt-3"><p className="mb-1 text-[14px] font-semibold">Not on your resume</p>
                <div className="flex flex-wrap gap-1.5">{data.keywords.missing.map((k) => <Chip key={k} tone="blocked">{k}</Chip>)}</div></div>
            )}
            {data.keywords.present.length > 0 && (
              <div className="mt-3"><p className="mb-1 text-[14px] font-semibold">Already on your resume</p>
                <div className="flex flex-wrap gap-1.5">{data.keywords.present.map((k) => <Chip key={k} tone="verified">{k}</Chip>)}</div></div>
            )}
          </>
        ) : <p className="text-muted">Import your resume in Career Profile to see which terms it already covers.</p>}
      </section>

      <div className="flex flex-col gap-3">
        <details className="rounded-[var(--radius-card)] border border-line p-4">
          <summary className="cursor-pointer font-semibold">Read the full posting</summary>
          <div className="mt-3 max-h-[28rem] overflow-y-auto text-[15px] whitespace-pre-line">{data.description}</div>
        </details>
        {data.fit_parts.length > 0 && (
          <details className="rounded-[var(--radius-card)] border border-line p-4">
            <summary className="cursor-pointer font-semibold">How the fit score is made</summary>
            <dl className="mt-3 grid grid-cols-[1fr_auto] gap-y-1">
              {data.fit_parts.map(([name, value]) => (
                <div key={name} className="contents"><dt>{name}</dt><dd className="font-semibold">{value}</dd></div>
              ))}
            </dl>
          </details>
        )}
        {data.url && (
          <LinkButton href={data.url} external className="self-start">
            Open the original posting <ExternalLink aria-hidden className="size-4" />
          </LinkButton>
        )}
      </div>
    </article>
  );
}
