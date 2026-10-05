"use client";

import { ArrowRight, Check, CircleAlert, Copy, Download, ExternalLink, Minus, X } from "lucide-react";
import { useState } from "react";
import { Alert, Button, Card, Chip, ErrorBox, LinkButton, PageHeader, Spinner, TextArea, cx, useToast } from "@/components/ui";
import { api, useResource } from "@/lib/api";
import type { ApplyPage, CheckItem, KitField } from "@/lib/types";

const CHECK = {
  ok: { icon: Check, className: "bg-verified-soft text-verified", word: "Ready" },
  review: { icon: CircleAlert, className: "bg-review-soft text-review", word: "Needs a look" },
  blocked: { icon: X, className: "bg-blocked-soft text-blocked", word: "Not ready" },
  neutral: { icon: Minus, className: "bg-canvas text-muted", word: "Info" },
} as const;

function Checklist({ items }: { items: CheckItem[] }) {
  return (
    <ul className="divide-y divide-line">
      {items.map((item) => {
        const c = CHECK[item.state] ?? CHECK.neutral;
        const Icon = c.icon;
        return (
          <li key={item.label} className="flex gap-3 py-3">
            <span className={`mt-0.5 flex size-6 shrink-0 items-center justify-center rounded-full ${c.className}`}>
              <Icon aria-hidden className="size-4" /><span className="sr-only">{c.word}:</span>
            </span>
            <span><span className="font-semibold">{item.label}</span><span className="block text-[15px] text-muted">{item.detail}</span></span>
          </li>
        );
      })}
    </ul>
  );
}

function CopyValue({ value, label }: { value: string; label: string }) {
  const toast = useToast();
  return (
    <div className="flex min-w-0 items-center gap-2 rounded-[var(--radius-control)] border border-line bg-canvas px-3 py-1.5">
      <span className="min-w-0 flex-1 break-words font-mono text-[14px]">{value}</span>
      <button type="button" aria-label={`Copy ${label}`}
        onClick={() => navigator.clipboard.writeText(value).then(() => toast(`${label} copied.`), () => toast("Copy didn't work; select the text instead."))}
        className="flex size-11 shrink-0 items-center justify-center rounded-[var(--radius-control)] text-muted hover:bg-paper hover:text-primary cursor-pointer">
        <Copy aria-hidden className="size-4" />
      </button>
    </div>
  );
}

function Kit({ fields, summary }: { fields: KitField[]; summary: string }) {
  const optional = fields.filter((f) => f.state === "optional").map((f) => f.label);
  return (
    <section aria-labelledby="kit">
      <h2 id="kit" className="text-[20px] font-semibold">Assist: your application kit</h2>
      <p className="text-[15px] text-muted">Open the employer&apos;s form beside this and copy each answer across. Everything here comes from your confirmed profile, your tailored resume and answers you approved. {summary}</p>
      <Card className="mt-3 p-0 sm:p-0">
        <dl className="divide-y divide-line">
          {fields.filter((f) => f.state !== "optional").map((f) => (
            <div key={f.label} className="grid gap-2 px-4 py-3 sm:grid-cols-[minmax(0,2fr)_minmax(0,3fr)] sm:items-center">
              <dt><span className="font-semibold">{f.label}</span><span className="block text-[13px] text-muted">{f.source}</span></dt>
              <dd className="min-w-0">
                {f.state === "ready" && f.label === "Resume" ? <span>{f.value} · use the download above</span>
                  : f.state === "ready" ? <CopyValue value={f.value} label={f.label} />
                  : <span className="flex items-center gap-2"><Chip tone="review">Missing</Chip> Add it in {f.fix}</span>}
              </dd>
            </div>
          ))}
        </dl>
      </Card>
      {optional.length > 0 && <p className="mt-2 text-[14px] text-muted">Not in your profile (often optional): {optional.join(", ")}.</p>}
    </section>
  );
}

function Questions() {
  const toast = useToast();
  const [result, setResult] = useState<{ readable: boolean; unanswered: string[]; used: Record<string, string> } | null>(null);
  const [typed, setTyped] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  async function check() {
    setBusy(true);
    try { setResult(await api("/apply/questions", { method: "POST" })); } catch (e) { toast((e as Error).message); } finally { setBusy(false); }
  }
  async function save() {
    const entries = Object.entries(typed).filter(([, a]) => a.trim());
    for (const [question, answer] of entries) await api("/answers", { method: "POST", json: { question, answer } });
    toast(`Saved ${entries.length} ${entries.length === 1 ? "answer" : "answers"}.`);
    setResult((r) => r && { ...r, unanswered: r.unanswered.filter((q) => !typed[q]?.trim()) });
  }
  return (
    <details className="rounded-[var(--radius-card)] border border-line bg-paper p-4">
      <summary className="cursor-pointer font-semibold">Check the form for custom questions</summary>
      <p className="mt-2 text-[15px] text-muted">Optional. Tries to read the employer&apos;s form so you can answer questions here once and reuse them.</p>
      <Button className="mt-3" busy={busy} onClick={check}>Check for questions</Button>
      {result && !result.readable && <div className="mt-3"><Alert tone="neutral">This employer&apos;s form can&apos;t be read automatically (most are built in the browser). You&apos;ll see any extra questions on their site.</Alert></div>}
      {result?.readable && result.unanswered.length === 0 && <div className="mt-3"><Alert tone="verified">No unanswered questions were found on the form.</Alert></div>}
      {result && Object.keys(result.used).length > 0 && (
        <div className="mt-3"><p className="font-semibold">Saved answers that match this form</p>
          <ul className="list-disc pl-5">{Object.entries(result.used).map(([q, a]) => <li key={q}>{q}: {a}</li>)}</ul></div>
      )}
      {result && result.unanswered.length > 0 && (
        <div className="mt-4 flex flex-col gap-3">
          <p className="font-semibold">Questions that need your answer</p>
          <p className="text-[14px] text-muted">Only answers you write here are saved and reused. Job Copilot never writes an answer for you.</p>
          {result.unanswered.map((q) => <TextArea key={q} label={q} rows={2} value={typed[q] ?? ""} onChange={(e) => setTyped({ ...typed, [q]: e.target.value })} />)}
          <Button variant="primary" className="self-start" onClick={save}>Approve and save answers</Button>
        </div>
      )}
    </details>
  );
}

export default function ApplyPageView() {
  const toast = useToast();
  const { data, error, loading, reload, set } = useResource<ApplyPage>("/apply");
  const [busy, setBusy] = useState<string | null>(null);

  async function act(path: string, message: string) {
    setBusy(path);
    try {
      set(await api<ApplyPage>(path, { method: "POST", json: path === "/apply/select" ? undefined : {} }));
      toast(message);
    } catch (e) {
      toast((e as Error).message);
    } finally {
      setBusy(null);
    }
  }

  const header = <PageHeader title="Apply" description="Check that everything is ready, then finish on the employer's own site. Job Copilot never submits for you." />;
  if (error) return <>{header}<ErrorBox error={error} retry={reload} /></>;
  if (loading && !data) return <>{header}<Spinner label="Checking readiness" /></>;
  if (!data) return null;

  if (!data.job || !data.view) {
    return (
      <>
        {header}
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_320px]">
          <Card>
            <h2 className="text-[22px] font-semibold">To prepare an application</h2>
            <p className="mt-1 text-muted">Apply checks that everything is ready, then sends you to the employer&apos;s own application. It never submits for you.</p>
            <ol className="mt-4 flex flex-col gap-2">
              {data.empty?.items.map((item, i) => (
                <li key={item.label} className="flex items-center justify-between gap-3 rounded-[var(--radius-control)] bg-canvas px-3 py-2">
                  <span>{i + 1}. {item.label}</span><Chip tone={item.done ? "verified" : "neutral"}>{item.done ? "Done" : "Not yet"}</Chip>
                </li>
              ))}
            </ol>
            {data.empty && <LinkButton href={data.empty.action_page} variant="primary" className="mt-5">{data.empty.action_label} <ArrowRight aria-hidden className="size-4" /></LinkButton>}
            {data.staged && data.staged.length > 0 && (
              <div className="mt-6">
                <h3 className="font-semibold">Or finish one you&apos;ve already staged</h3>
                <ul className="mt-2 flex flex-col gap-2">
                  {data.staged.map((s) => (
                    <li key={s.job_id}>
                      <Button busy={busy === s.job_id} onClick={async () => {
                        setBusy(s.job_id);
                        try { set(await api<ApplyPage>("/apply/select", { method: "POST", json: { job_id: s.job_id } })); }
                        catch (e) { toast((e as Error).message); } finally { setBusy(null); }
                      }}>{s.title} at {s.company}</Button>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </Card>
          <Card>
            <h2 className="text-[18px] font-semibold">You stay in control</h2>
            <p className="mt-2 text-muted">You finish on the employer&apos;s site with your tailored resume, then mark it as applied. Job Copilot never submits an application for you.</p>
          </Card>
        </div>
      </>
    );
  }

  const v = data.view;
  const tone = { ready: "verified", tracked: "verified", applied: "verified", not_ready: "review" }[v.stage] as "verified" | "review";
  const stepState = (done: boolean, current: boolean) => (done ? "complete" : current ? "current" : "pending");
  const used = v.stage === "tracked" || v.stage === "applied"; // a tracked application already had its resume
  const resumeDone = Boolean(data.handoff) || used;
  const steps = [
    { label: "Resume ready", state: stepState(resumeDone, !resumeDone) },
    { label: "Tracked", state: stepState(used, Boolean(data.handoff) && v.stage === "ready") },
    { label: "Marked as applied", state: stepState(v.stage === "applied", v.stage === "tracked") },
  ];

  return (
    <>
      {header}
      <ol aria-label="Application readiness" className="mb-6 grid grid-cols-1 gap-2 sm:grid-cols-3">
        {steps.map((s) => (
          <li key={s.label} className={cx("rounded-[var(--radius-control)] border-t-4 bg-paper px-3 py-2 text-[14px] font-semibold",
            s.state === "complete" ? "border-verified text-verified" : s.state === "current" ? "border-primary" : "border-line text-muted")}>
            {s.label}<span className="sr-only"> — {s.state}</span>
          </li>
        ))}
      </ol>
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
        <div className="flex flex-col gap-6">
          <Card>
            <p className="text-[14px] font-semibold tracking-wide text-muted uppercase">{data.job.company}</p>
            <h2 className="mt-1 text-[24px] font-semibold">{data.job.title}</h2>
            <div className="mt-3"><Alert tone={tone}>{v.headline}</Alert></div>
            <div className="mt-2"><Checklist items={v.checklist} /></div>
            <div className="mt-4 flex flex-wrap gap-2">
              {v.can_open
                ? <LinkButton href={data.job.url} external variant="primary">Open employer application <ExternalLink aria-hidden className="size-4" /></LinkButton>
                : <Button variant="primary" disabled>Open employer application</Button>}
              <Button busy={busy === "/apply/track"} disabled={!v.can_track} onClick={() => act("/apply/track", "Tracked as ready to apply.")}
                title="Adds it to Tracker as ready to apply. Doesn't submit anything.">Track this application</Button>
              <Button busy={busy === "/apply/applied"} disabled={!v.can_mark_applied} onClick={() => act("/apply/applied", "Marked as applied.")}
                title="Use this after you've submitted on the employer's site.">Mark as applied</Button>
            </div>
            {v.stage === "tracked" && <p className="mt-3 text-[14px] text-muted">Opening the employer&apos;s page doesn&apos;t submit anything. Mark it as applied once you&apos;ve finished there.</p>}
            {v.stage === "applied" && <LinkButton href="/tracker" variant="ghost" className="mt-3">Open Tracker <ArrowRight aria-hidden className="size-4" /></LinkButton>}
            {!data.handoff && !used && <LinkButton href="/tailor" variant="ghost" className="mt-3">Tailor your resume for this job <ArrowRight aria-hidden className="size-4" /></LinkButton>}
            {data.handoff?.has_file && (
              <a href="/api/backend/apply/resume" download className="mt-4 inline-flex min-h-11 items-center gap-2 font-semibold text-primary hover:underline">
                <Download aria-hidden className="size-4" /> Download the tailored resume to attach (version {data.handoff.version})
              </a>
            )}
          </Card>
          {data.kit && <Kit fields={data.kit} summary={data.kit_summary ?? ""} />}
          {data.helper_code && (
            <details className="rounded-[var(--radius-card)] border border-line bg-paper p-4">
              <summary className="cursor-pointer font-semibold">Fill the form for me with the browser helper</summary>
              <ol className="mt-3 list-decimal pl-5 text-[15px]">
                <li>Install the Job Copilot form helper in Chrome or Edge (the repo&apos;s <code>extension</code> folder; its README has the steps).</li>
                <li>Copy the helper code below and paste it into the helper once. It stays in your browser only.</li>
                <li>Open the employer&apos;s application and click <strong>Fill this page</strong>. Green fields were filled from your kit; amber ones are left for you. Attach your resume, check everything, then submit yourself.</li>
              </ol>
              <div className="mt-3"><CopyValue value={data.helper_code} label="Helper code" /></div>
            </details>
          )}
          <Questions />
        </div>
        <aside className="flex flex-col gap-4">
          <Card>
            <h2 className="text-[18px] font-semibold">How you&apos;ll apply</h2>
            <ul className="mt-3 flex flex-col gap-3">
              {v.modes.map((m) => (
                <li key={m.name}>
                  <p className="flex items-center gap-2 font-semibold">{m.name}
                    <Chip tone={m.available ? "verified" : "neutral"}>{m.available ? (m.recommended ? "Recommended" : "Available") : m.name === "Auto" ? "Not offered" : "Not available yet"}</Chip></p>
                  <p className="text-[14px] text-muted">{m.detail}</p>
                </li>
              ))}
            </ul>
          </Card>
          <Card>
            <h2 className="text-[18px] font-semibold">Saved answers</h2>
            <p className="mt-2 text-[15px] text-muted">Answers you&apos;ve approved for application questions live in your Career Profile.</p>
            <LinkButton href="/profile" variant="ghost" className="mt-2">Manage saved answers</LinkButton>
          </Card>
        </aside>
      </div>
    </>
  );
}
