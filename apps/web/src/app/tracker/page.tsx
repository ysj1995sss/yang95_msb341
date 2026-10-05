"use client";

import { ArrowLeft, ExternalLink, Inbox, Mail } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { Alert, Button, Card, Chip, ErrorBox, LinkButton, PageHeader, SelectField, Spinner, TextArea, TextField, cx, useToast } from "@/components/ui";
import { api, useResource } from "@/lib/api";
import type { ApplicationDetail, EmailReading, GmailStatus, GmailSuggestion, TrackerBoard } from "@/lib/types";

const STATUS_TONE: Record<string, "verified" | "review" | "blocked" | "primary" | "neutral"> = {
  offer: "verified", rejected: "blocked", withdrawn: "neutral", interview: "primary", final_interview: "primary",
  recruiter_screen: "primary", assessment: "review", ready_to_apply: "review", applied: "neutral",
};

function EmailPanel({ onApplied }: { onApplied: () => void }) {
  const toast = useToast();
  const [text, setText] = useState("");
  const [reading, setReading] = useState<EmailReading | null>(null);
  const [choice, setChoice] = useState({ application_id: "", status: "", email_date: "" });
  const [busy, setBusy] = useState(false);

  async function read() {
    setBusy(true);
    try {
      const r = await api<EmailReading>("/tracker/email/read", { method: "POST", json: { text } });
      setReading(r);
      setChoice({ application_id: r.chosen ?? "", status: r.status ?? "", email_date: r.email_date ?? new Date().toISOString().slice(0, 10) });
    } catch (e) { toast((e as Error).message); } finally { setBusy(false); }
  }
  async function confirm() {
    setBusy(true);
    try {
      await api("/tracker/email/confirm", { method: "POST", json: { ...choice, evidence: reading?.subject || reading?.phrase || "" } });
      toast(`Updated to ${reading?.status_label || "the new status"}.`);
      setText(""); setReading(null); onApplied();
    } catch (e) { toast((e as Error).message); } finally { setBusy(false); }
  }
  const option = reading?.options.find((o) => o.application_id === choice.application_id);

  return (
    <details className="mb-6 rounded-[var(--radius-card)] border border-line bg-paper p-4">
      <summary className="flex cursor-pointer items-center gap-2 font-semibold"><Mail aria-hidden className="size-4 text-primary" /> Update a status from a recruiter email</summary>
      <p className="mt-2 text-[15px] text-muted">Paste the email, with its From, Date and Subject lines if you have them. Job Copilot suggests the application and status; nothing changes until you confirm.</p>
      <div className="mt-3 flex flex-col gap-3">
        <TextArea label="Recruiter email" rows={6} value={text} onChange={(e) => { setText(e.target.value); setReading(null); }} />
        <Button className="self-start" busy={busy && !reading} disabled={!text.trim()} onClick={read}>Read the email</Button>
        {reading && !reading.status && <Alert tone="neutral">This email doesn&apos;t clearly say a status (a rejection, assessment, interview, offer and so on), so there&apos;s nothing to update.</Alert>}
        {reading?.status && (
          <div className="flex flex-col gap-3 rounded-[var(--radius-card)] border border-primary/30 bg-primary-soft p-4">
            <p>Suggested status: <strong>{reading.status_label}</strong>, because it says &ldquo;{reading.phrase}&rdquo;.</p>
            <SelectField label="Which application is this about?" value={choice.application_id}
              options={[{ value: "", label: "Choose the application" }, ...reading.options.map((o) => ({ value: o.application_id, label: o.label }))]}
              onChange={(e) => setChoice({ ...choice, application_id: e.target.value })}
              help={reading.chosen ? undefined : "The email doesn't clearly point to one tracked application, so choose it yourself."} />
            <TextField label="Email date" type="date" value={choice.email_date} onChange={(e) => setChoice({ ...choice, email_date: e.target.value })} />
            {option?.backwards && <Alert tone="review">This would move it back to an earlier stage. Confirm only if that&apos;s right.</Alert>}
            <Button variant="primary" className="self-start" busy={busy} disabled={!choice.application_id} onClick={confirm}>Confirm update</Button>
          </div>
        )}
      </div>
    </details>
  );
}

const GMAIL_RESULT: Record<string, { tone: "verified" | "review"; text: string }> = {
  connected: { tone: "verified", text: "Gmail is connected. Check it for recruiter emails below." },
  declined: { tone: "review", text: "Gmail wasn't connected: the read-only permission wasn't granted." },
  expired: { tone: "review", text: "That Gmail connection attempt expired. Try again." },
  failed: { tone: "review", text: "Gmail couldn't be connected. Try again in a minute." },
};

function GmailSuggestionCard({ s, onDone }: { s: GmailSuggestion; onDone: (message: string) => void }) {
  const toast = useToast();
  const [applicationId, setApplicationId] = useState(s.chosen ?? "");
  const [busy, setBusy] = useState(false);
  const option = s.options.find((o) => o.application_id === applicationId);

  async function confirm() {
    setBusy(true);
    try {
      await api("/tracker/email/confirm", { method: "POST",
        json: { application_id: applicationId, status: s.status, email_date: s.email_date, evidence: s.subject || s.phrase } });
      await api("/gmail/dismiss", { method: "POST", json: { message_id: s.message_id } });
      onDone(`Updated to ${s.status_label}.`);
    } catch (e) { toast((e as Error).message); setBusy(false); }
  }
  async function dismiss() {
    setBusy(true);
    try {
      await api("/gmail/dismiss", { method: "POST", json: { message_id: s.message_id } });
      onDone("Dismissed. It won't be suggested again.");
    } catch (e) { toast((e as Error).message); setBusy(false); }
  }

  return (
    <li className="flex flex-col gap-3 rounded-[var(--radius-card)] border border-line bg-canvas p-4">
      <div>
        <p className="font-semibold">{s.subject || "(no subject)"}</p>
        <p className="text-[14px] text-muted">{s.from}{s.email_date ? ` · ${s.email_date.slice(0, 10)}` : ""}</p>
      </div>
      <p>Suggested status: <strong>{s.status_label}</strong>, because it says &ldquo;{s.phrase}&rdquo;.</p>
      <SelectField label="Which application is this about?" value={applicationId}
        options={[{ value: "", label: "Choose the application" }, ...s.options.map((o) => ({ value: o.application_id, label: o.label }))]}
        onChange={(e) => setApplicationId(e.target.value)}
        help={s.chosen ? undefined : "The email doesn't clearly point to one tracked application, so choose it yourself."} />
      {option?.backwards && <Alert tone="review">This would move it back to an earlier stage. Confirm only if that&apos;s right.</Alert>}
      <div className="flex flex-wrap gap-2">
        <Button variant="primary" busy={busy} disabled={!applicationId} onClick={confirm}>Confirm update</Button>
        <Button disabled={busy} onClick={dismiss}>Not about my application</Button>
      </div>
    </li>
  );
}

function GmailPanel({ onApplied }: { onApplied: () => void }) {
  const toast = useToast();
  const result = GMAIL_RESULT[useSearchParams().get("gmail") ?? ""];
  const { data: status, reload } = useResource<GmailStatus>("/gmail");
  const [found, setFound] = useState<GmailSuggestion[] | null>(null);
  const [busy, setBusy] = useState(false);
  if (!status?.available) return null;

  async function scan() {
    setBusy(true);
    try {
      setFound((await api<{ suggestions: GmailSuggestion[] }>("/gmail/scan", { method: "POST" })).suggestions);
      reload();
    } catch (e) { toast((e as Error).message); } finally { setBusy(false); }
  }
  async function disconnect() {
    setBusy(true);
    try {
      await api("/gmail", { method: "DELETE" });
      setFound(null); reload(); toast("Gmail is disconnected and Job Copilot's access was removed.");
    } catch (e) { toast((e as Error).message); } finally { setBusy(false); }
  }

  return (
    <section aria-labelledby="gmail-heading" className="mb-6 rounded-[var(--radius-card)] border border-line bg-paper p-4">
      <h2 id="gmail-heading" className="flex items-center gap-2 font-semibold"><Inbox aria-hidden className="size-4 text-primary" /> Recruiter emails from Gmail</h2>
      {result && <div className="mt-3"><Alert tone={result.tone}>{result.text}</Alert></div>}
      {!status.connected ? (
        <>
          <p className="mt-2 text-[15px] text-muted">Job Copilot can read emails from job-application systems (Greenhouse, Lever, Ashby, Workday, SmartRecruiters) from the last 30 days and suggest status updates. Google asks for read-only access to your whole mailbox, but Job Copilot only looks at those senders, never sends or changes email, and nothing in Tracker changes until you confirm. You can disconnect at any time.</p>
          <a href="/api/gmail/connect" className="mt-3 inline-flex min-h-11 items-center rounded-[var(--radius-control)] border border-line-strong bg-paper px-4 font-semibold hover:bg-canvas">Connect Gmail</a>
        </>
      ) : (
        <>
          <p className="mt-2 text-[15px] text-muted">
            Connected. {status.last_scan ? `Last checked ${new Date(status.last_scan).toLocaleString()}.` : "Not checked yet."} Nothing in Tracker changes until you confirm a suggestion.
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            <Button variant="primary" busy={busy && !found} onClick={scan}>Check Gmail now</Button>
            <Button disabled={busy} onClick={disconnect}>Disconnect Gmail</Button>
          </div>
          {found && found.length === 0 && <p className="mt-3" role="status">No new status updates in recruiter emails from the last 30 days.</p>}
          {found && found.length > 0 && (
            <ul className="mt-4 flex flex-col gap-3" aria-label="Suggested status updates">
              {found.map((s) => (
                <GmailSuggestionCard key={s.message_id} s={s} onDone={(message) => {
                  toast(message); setFound((list) => (list ?? []).filter((x) => x.message_id !== s.message_id)); onApplied();
                }} />
              ))}
            </ul>
          )}
        </>
      )}
    </section>
  );
}

function Detail({ id, onChanged, onBack }: { id: string; onChanged: () => void; onBack: () => void }) {
  const toast = useToast();
  const router = useRouter();
  const { data, error, reload, set } = useResource<ApplicationDetail>(`/tracker/${encodeURIComponent(id)}`);
  const [next, setNext] = useState<ApplicationDetail["next_action"] | null>(null);
  const [status, setStatus] = useState<{ value: string; note: string } | null>(null);
  if (error) return <ErrorBox error={error} retry={reload} />;
  if (!data) return <Spinner label="Loading the application" />;
  const n = next ?? data.next_action;
  const s = status ?? { value: data.row.status, note: "" };

  async function save(path: string, json: unknown, message: string, method = "PUT") {
    try {
      set(await api<ApplicationDetail>(path, { method, json }));
      toast(message); setNext(null); setStatus(null); onChanged();
    } catch (e) { toast((e as Error).message); }
  }

  return (
    <article aria-labelledby="app-title" className="flex flex-col gap-5">
      <Button variant="ghost" className="self-start lg:hidden" onClick={onBack}><ArrowLeft aria-hidden className="size-4" /> Back to applications</Button>
      <h2 id="app-title" className="text-[22px] font-semibold">{data.row.role} at {data.row.company}</h2>
      <dl className="grid grid-cols-[minmax(0,12rem)_1fr] gap-x-4 gap-y-1.5 text-[15px]">
        {data.facts.map((f) => <div key={f.label} className="contents"><dt className="text-muted">{f.label}</dt><dd className="font-semibold">{f.value}</dd></div>)}
      </dl>
      <p className="text-[14px] text-muted">This is what was true when the application was recorded; later edits don&apos;t change it.</p>

      <section aria-labelledby="next-action" className="flex flex-col gap-3 rounded-[var(--radius-card)] border border-line p-4">
        <h3 id="next-action" className="font-semibold">Next action</h3>
        <TextField label="What's next" placeholder="e.g. Email the recruiter" value={n.text} onChange={(e) => setNext({ ...n, text: e.target.value })} />
        <TextField label="Due" type="date" value={n.due} onChange={(e) => setNext({ ...n, due: e.target.value })} />
        <TextArea label="Notes" rows={2} value={n.notes} onChange={(e) => setNext({ ...n, notes: e.target.value })} />
        <Button className="self-start" disabled={!next} onClick={() => save(`/tracker/${id}/next-action`, { text: n.text, due: n.due || null, notes: n.notes }, "Next action saved.")}>Save next action</Button>
      </section>

      <section aria-labelledby="move" className="flex flex-col gap-3 rounded-[var(--radius-card)] border border-line p-4">
        <h3 id="move" className="font-semibold">Move status</h3>
        <SelectField label="New status" value={s.value} options={data.status_options} onChange={(e) => setStatus({ ...s, value: e.target.value })} />
        <TextField label="Note (optional)" value={s.note} onChange={(e) => setStatus({ ...s, note: e.target.value })} />
        <Button variant="primary" className="self-start" disabled={s.value === data.row.status}
          onClick={() => save(`/tracker/${id}/status`, { status: s.value, note: s.note }, "Status saved.", "POST")}>Save status</Button>
      </section>

      <details open className="rounded-[var(--radius-card)] border border-line p-4">
        <summary className="cursor-pointer font-semibold">Status history</summary>
        <ol className="mt-2 flex flex-col gap-1.5 text-[15px]">
          {data.history.map((h, i) => (
            <li key={`${h.when}-${i}`}><span className="text-muted">{new Date(h.when).toLocaleString(undefined, { month: "short", day: "numeric", year: "numeric", hour: "numeric", minute: "2-digit" })} · </span>
              <strong>{h.status}</strong> · set by {h.who}{h.note ? ` · ${h.note}` : ""}</li>
          ))}
        </ol>
      </details>
      <details className="rounded-[var(--radius-card)] border border-line p-4">
        <summary className="cursor-pointer font-semibold">Answers used ({data.answers.length})</summary>
        {data.answers.length ? <ul className="mt-2 list-disc pl-5">{data.answers.map((a) => <li key={a.question}><strong>{a.question}</strong> {a.answer}</li>)}</ul>
          : <p className="mt-2 text-muted">No saved answers were used for this application.</p>}
      </details>
      <div className="flex flex-wrap gap-2">
        {data.row.url && <LinkButton href={data.row.url} external>Open employer page <ExternalLink aria-hidden className="size-4" /></LinkButton>}
        <Button onClick={async () => {
          try { const r = await api<{ next: string }>(`/tracker/${id}/retailor`, { method: "POST" }); router.push(r.next); }
          catch (e) { toast((e as Error).message); }
        }}>Tailor again for this job</Button>
      </div>
    </article>
  );
}

export default function TrackerPage() {
  const toast = useToast();
  const [view, setView] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState<string | null>(null);
  const [showDetail, setShowDetail] = useState(false);
  const path = `/tracker?${new URLSearchParams({ ...(view ? { view } : {}), q: query })}`;
  const { data, error, loading, reload } = useResource<TrackerBoard>(path);
  const [goal, setGoal] = useState<number | null>(null);

  const header = <PageHeader title="Tracker" description="Every application, its exact record, and what to do next." />;
  if (error) return <>{header}<ErrorBox error={error} retry={reload} /></>;
  if (!data) return <>{header}<Spinner label="Loading applications" /></>;

  if (data.total === 0) {
    return (
      <>
        {header}
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_320px]">
          <Card>
            <h2 className="text-[22px] font-semibold">Nothing tracked yet</h2>
            <p className="mt-1 text-muted">When you choose <strong>Track this application</strong> on Apply, it appears here with:</p>
            <ul className="mt-3 list-disc pl-5">
              <li>The exact job posting, as it was when you applied</li>
              <li>The tailored resume version and any saved answers you used</li>
              <li>Every status change, who made it, and when</li>
            </ul>
            <p className="mt-3 text-[14px] text-muted">Status: {data.lifecycle.join(" → ")}</p>
            <LinkButton href="/jobs" variant="primary" className="mt-5">Find a job</LinkButton>
          </Card>
          <Card><h2 className="text-[18px] font-semibold">Next actions</h2><p className="mt-2 text-muted">Give each application a next step and a due date. Anything due shows up first on Home and under Needs action here.</p></Card>
        </div>
      </>
    );
  }

  const current = data.rows.find((r) => r.application_id === selected)?.application_id ?? data.rows[0]?.application_id ?? null;
  const weeklyGoal = goal ?? data.weekly_goal;
  return (
    <>
      {header}
      <Suspense fallback={null}><GmailPanel onApplied={reload} /></Suspense>
      <EmailPanel onApplied={reload} />
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,1fr)_300px]">
        <div className="min-w-0">
          <div role="group" aria-label="Saved views" className="mb-3 flex flex-wrap gap-1.5">
            {data.views.map((v) => (
              <button key={v.name} type="button" aria-pressed={data.view === v.name}
                onClick={() => { setView(v.name); setSelected(null); setShowDetail(false); }}
                className={cx("min-h-11 rounded-full border px-3.5 text-[14px] font-semibold transition-colors duration-150 cursor-pointer",
                  data.view === v.name ? "border-primary bg-primary text-on-primary" : "border-line-strong bg-paper hover:bg-canvas")}>
                {v.name} ({v.count})
              </button>
            ))}
          </div>
          <TextField label="Search company or role" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Type to filter" className="mb-4 max-w-md" />
          {loading && <p className="sr-only" role="status">Updating…</p>}
          {data.rows.length === 0 ? <Card><p className="text-muted">{query ? "No applications match that search." : "Nothing in this view."}</p></Card> : (
            <div className="grid grid-cols-1 gap-6 xl:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
              <Card className={cx("p-0 sm:p-0 xl:block", showDetail && "hidden")} aria-labelledby="apps-heading">
                <h2 id="apps-heading" className="sr-only">Applications</h2>
                <ul className="divide-y divide-line">
                  {data.rows.map((r) => (
                    <li key={r.application_id}>
                      <button type="button" aria-current={r.application_id === current ? "true" : undefined}
                        onClick={() => { setSelected(r.application_id); setShowDetail(true); window.scrollTo({ top: 0 }); }}
                        className={cx("flex w-full flex-col gap-1 border-l-4 px-4 py-3 text-left transition-colors duration-150 cursor-pointer",
                          r.application_id === current ? "border-primary bg-primary-soft" : "border-transparent hover:bg-canvas")}>
                        <span className="font-semibold">{r.role}</span>
                        <span className="text-[14px] text-muted">{r.company}{r.applied ? ` · applied ${r.applied}` : ""}</span>
                        <span className="flex flex-wrap items-center gap-1.5">
                          <Chip tone={STATUS_TONE[r.status] ?? "neutral"}>{r.status_label}</Chip>
                          {r.next_action && <span className="text-[13px] text-muted">Next: {r.next_action}{r.due ? ` · due ${r.due}` : ""}</span>}
                        </span>
                      </button>
                    </li>
                  ))}
                </ul>
              </Card>
              <div className={cx("xl:block", !showDetail && "hidden")}>
                {current && <Card><Detail key={current} id={current} onChanged={reload} onBack={() => setShowDetail(false)} /></Card>}
              </div>
            </div>
          )}
        </div>
        <aside>
          <Card aria-labelledby="this-week">
            <h2 id="this-week" className="text-[18px] font-semibold">Week of {new Date(`${data.weekly.week_start}T00:00`).toLocaleDateString(undefined, { month: "short", day: "numeric" })}</h2>
            <p className="mt-2 font-[family-name:var(--font-heading)] text-[40px] leading-none font-semibold">{data.weekly.applied}</p>
            <p className="text-muted">applications sent</p>
            {weeklyGoal > 0 && (
              <>
                <div className="mt-3 h-2 rounded-full bg-line" role="progressbar" aria-label="Weekly goal" aria-valuemin={0} aria-valuemax={weeklyGoal} aria-valuenow={Math.min(data.weekly.applied, weeklyGoal)}>
                  <div className="h-2 rounded-full bg-primary" style={{ width: `${Math.min(100, (data.weekly.applied / weeklyGoal) * 100)}%` }} />
                </div>
                <p className="mt-2 text-[14px] text-muted">{data.weekly.applied} of {weeklyGoal}. A goal is a pace, not a test.</p>
              </>
            )}
            <p className="mt-3 text-[15px]">{data.weekly.interviews} in interviews · {data.weekly.saved} saved, not applied</p>
            <form className="mt-4 flex items-end gap-2" onSubmit={async (e) => {
              e.preventDefault();
              try { const r = await api<{ weekly_goal: number }>("/tracker/weekly-goal", { method: "PUT", json: { goal: weeklyGoal } }); setGoal(r.weekly_goal); toast("Weekly goal saved."); }
              catch (err) { toast((err as Error).message); }
            }}>
              <TextField label="Weekly goal (0 for none)" type="number" min={0} max={100} value={weeklyGoal} className="w-40"
                onChange={(e) => setGoal(Math.max(0, Math.min(100, Number(e.target.value) || 0)))} />
              <Button type="submit">Save</Button>
            </form>
          </Card>
        </aside>
      </div>
    </>
  );
}
