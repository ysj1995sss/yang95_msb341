"use client";

import { ExternalLink, Layers } from "lucide-react";
import { useEffect, useState } from "react";
import { Alert, Button, Card, Chip, useToast } from "@/components/ui";
import { api, useResource } from "@/lib/api";
import type { Batch, PrepareResult } from "@/lib/types";

const ITEM_STATUS: Record<string, { label: string; tone: "verified" | "primary" | "review" | "blocked" | "neutral" }> = {
  queued: { label: "Waiting", tone: "neutral" },
  running: { label: "Tailoring now", tone: "primary" },
  done: { label: "Tailored", tone: "verified" },
  failed: { label: "Failed", tone: "blocked" },
  skipped: { label: "Skipped", tone: "review" },
  not_started: { label: "Not started", tone: "review" },
};

function useBatch() {
  const resource = useResource<{ batch: Batch | null }>("/batch");
  const running = resource.data?.batch?.status === "running";
  const { reload } = resource;
  useEffect(() => {
    if (!running) return;
    const timer = setInterval(reload, 2000);
    return () => clearInterval(timer);
  }, [running, reload]);
  return resource;
}

/** Spec 011: the batch in progress on Tailor, with a way to open each job's review. */
export function BatchStrip({ onOpened, currentJobId }: { onOpened: () => void; currentJobId?: string | null }) {
  const toast = useToast();
  const { data, reload } = useBatch();
  const [busy, setBusy] = useState<string | null>(null);
  const batch = data?.batch;
  if (!batch) return null;

  async function open(jobId: string) {
    setBusy(jobId);
    try {
      await api("/batch/open", { method: "POST", json: { job_id: jobId } });
      onOpened();
    } catch (e) { toast((e as Error).message); } finally { setBusy(null); }
  }
  async function cancel() {
    await api("/batch", { method: "DELETE" });
    reload();
  }

  return (
    <Card className="mb-6" aria-labelledby="batch-heading">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 id="batch-heading" className="flex items-center gap-2 text-[18px] font-semibold"><Layers aria-hidden className="size-5 text-primary" /> Batch</h2>
        <p className="text-[15px] text-muted" role="status">{batch.summary}</p>
      </div>
      {batch.note && <div className="mt-2"><Alert tone="review">{batch.note}</Alert></div>}
      <ul className="mt-3 flex flex-col gap-1.5">
        {batch.items.map((item) => {
          const s = ITEM_STATUS[item.status] ?? ITEM_STATUS.queued;
          const isOpen = item.job_id === currentJobId;
          return (
            <li key={item.job_id} className="flex flex-wrap items-center gap-2 rounded-[var(--radius-control)] bg-canvas px-3 py-2">
              <span className="min-w-0 flex-1"><span className="font-semibold">{item.title}</span> <span className="text-muted">at {item.company}</span>
                {item.error && <span className="block text-[14px] text-muted">{item.error}</span>}</span>
              <Chip tone={s.tone}>{s.label}</Chip>
              {item.status === "done" && (isOpen
                ? <Chip tone="primary">Open now</Chip>
                : <Button busy={busy === item.job_id} onClick={() => open(item.job_id)}>Open review</Button>)}
            </li>
          );
        })}
      </ul>
      {batch.status === "running" && <Button variant="ghost" className="mt-3" onClick={cancel}>Stop after the current job</Button>}
    </Card>
  );
}

const PREPARED: Record<string, { label: string; tone: "verified" | "review" | "blocked" | "neutral" }> = {
  tracked: { label: "Ready to apply", tone: "verified" },
  already_tracked: { label: "Already tracked", tone: "neutral" },
  review_first: { label: "Review first", tone: "review" },
  not_found: { label: "Not found", tone: "blocked" },
};

/** Spec 011: track every reviewed, passing batch job as "Ready to apply". Never submits. */
export function BatchPrepare({ onPrepared }: { onPrepared?: () => void }) {
  const toast = useToast();
  const { data } = useBatch();
  const [busy, setBusy] = useState(false);
  const [results, setResults] = useState<PrepareResult[] | null>(null);
  const batch = data?.batch;
  if (!batch || !batch.items.some((i) => i.status === "done")) return null;

  async function prepare() {
    setBusy(true);
    try {
      const r = await api<{ results: PrepareResult[] }>("/batch/prepare", { method: "POST", json: {} });
      setResults(r.results);
      onPrepared?.();
    } catch (e) { toast((e as Error).message); } finally { setBusy(false); }
  }

  return (
    <Card className="mb-6" aria-labelledby="batch-prepare-heading">
      <h2 id="batch-prepare-heading" className="text-[18px] font-semibold">Your batch</h2>
      <p className="mt-1 text-[15px] text-muted">
        Prepare every batch job whose review you finished and whose resume passed its checks. Each is tracked as ready to
        apply; you still apply on each employer&apos;s own site. Nothing is submitted for you.
      </p>
      <Button variant="primary" className="mt-3" busy={busy} onClick={prepare}>Prepare reviewed jobs for applying</Button>
      {results && (
        <ul className="mt-4 flex flex-col gap-1.5" aria-label="Preparation results">
          {results.map((r) => {
            const s = PREPARED[r.status] ?? PREPARED.not_found;
            return (
              <li key={r.job_id} className="flex flex-wrap items-center gap-2 rounded-[var(--radius-control)] bg-canvas px-3 py-2">
                <span className="min-w-0 flex-1"><span className="font-semibold">{r.title || r.job_id}</span> <span className="text-muted">{r.company && `at ${r.company}`}</span>
                  {r.message && <span className="block text-[14px] text-muted">{r.message}</span>}</span>
                <Chip tone={s.tone}>{s.label}</Chip>
                {r.status === "tracked" && r.url && (
                  <a href={r.url} target="_blank" rel="noreferrer" className="inline-flex min-h-11 items-center gap-1.5 font-semibold text-primary underline-offset-2 hover:underline">
                    Employer&apos;s application <ExternalLink aria-hidden className="size-4" /><span className="sr-only"> (opens in a new tab)</span>
                  </a>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </Card>
  );
}
