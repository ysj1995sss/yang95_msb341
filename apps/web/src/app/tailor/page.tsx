"use client";

import { ArrowRight, Loader2, Wand2 } from "lucide-react";
import { useEffect, useState } from "react";
import { Alert, Button, Card, Checkbox, Chip, ErrorBox, LinkButton, PageHeader, RadioGroup, Spinner, TextArea, TextField, toneOf, useToast } from "@/components/ui";
import { api, useResource } from "@/lib/api";
import type { Review, RunStatus, TailorPage } from "@/lib/types";
import { ReviewRoom } from "./review";

const LENGTHS = [
  { value: "preserve", label: "Keep the original length" },
  { value: "1_page", label: "1 page" },
  { value: "2_page", label: "2 pages" },
] as const;

function Context({ page }: { page: TailorPage }) {
  const job = page.job!;
  const review = page.review;
  return (
    <Card className="mb-6">
      <p className="text-[14px] font-semibold tracking-wide text-muted uppercase">{job.company || "Pasted job description"}</p>
      <h2 className="mt-1 text-[24px] font-semibold">{job.title}</h2>
      <div className="mt-3 flex flex-wrap gap-2">
        <Chip tone="primary">{`Candidate fit ${job.fit === null ? "not assessed" : `${job.fit}%`}`}</Chip>
        <Chip>{`Resume alignment ${review?.alignment.after != null ? `${Math.round(review.alignment.after * 100)}%` : "after tailoring"}`}</Chip>
        {review && <Chip tone={toneOf(review.status_tone)}>{review.status_text}</Chip>}
      </div>
      <p className="mt-2 text-[14px] text-muted">Candidate fit measures your background. Resume alignment measures how clearly this resume shows it. They are never combined.</p>
    </Card>
  );
}

function PastedJobForm({ onDone }: { onDone: (page: TailorPage) => void }) {
  const [job, setJob] = useState({ title: "", company: "", url: "", description: "" });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  return (
    <form className="flex flex-col gap-4" onSubmit={async (e) => {
      e.preventDefault();
      setBusy(true);
      setError(null);
      try { onDone(await api<TailorPage>("/tailor/pasted", { method: "POST", json: job })); }
      catch (err) { setError((err as Error).message); } finally { setBusy(false); }
    }}>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <TextField label="Job title" required value={job.title} onChange={(e) => setJob({ ...job, title: e.target.value })} />
        <TextField label="Company" value={job.company} onChange={(e) => setJob({ ...job, company: e.target.value })} />
      </div>
      <TextField label="Link to the posting" help="Optional. Apply uses it to open the employer's application." type="url"
        value={job.url} onChange={(e) => setJob({ ...job, url: e.target.value })} />
      <TextArea label="Job description" help="Paste the whole posting, including requirements." rows={10} required
        value={job.description} onChange={(e) => setJob({ ...job, description: e.target.value })} />
      {error && <Alert tone="blocked" role="alert">{error}</Alert>}
      <Button type="submit" variant="primary" className="self-start" busy={busy} disabled={!job.title.trim() || !job.description.trim()}>
        Use this job
      </Button>
    </form>
  );
}

export default function TailorPageView() {
  const toast = useToast();
  const { data, error, loading, reload, set } = useResource<TailorPage>("/tailor");
  const [length, setLength] = useState<(typeof LENGTHS)[number]["value"]>("preserve");
  const [lightTouch, setLightTouch] = useState(false);
  const [starting, setStarting] = useState(false);
  const [startError, setStartError] = useState<string | null>(null);
  const [redo, setRedo] = useState(false);
  const [model, setModel] = useState({ model: "", api_key: "", api_base: "" });
  const running = data?.run.status === "running";

  // While a run is in progress, ask for its status every 1.5 s (never more than one request in flight).
  useEffect(() => {
    if (!running) return;
    let cancelled = false;
    const timer = setInterval(async () => {
      try {
        const status = await api<RunStatus>("/tailor/run");
        if (cancelled) return;
        if (status.status === "running") set({ ...data!, run: status });
        else reload();
      } catch {
        /* the next tick retries */
      }
    }, 1500);
    return () => { cancelled = true; clearInterval(timer); };
  }, [running, data, set, reload]);

  async function start() {
    setStarting(true);
    setStartError(null);
    try {
      const run = await api<RunStatus>("/tailor/run", { method: "POST", json: { length, conservative: lightTouch, ...model } });
      set({ ...data!, run, review: null });
      setRedo(false);
    } catch (e) {
      setStartError((e as Error).message);
    } finally {
      setStarting(false);
    }
  }

  async function discard() {
    await api("/tailor/review", { method: "DELETE" });
    toast("Review discarded. Tailor again when you're ready.");
    setRedo(true);
    reload();
  }

  async function oneOff(file: File | null) {
    if (!file) {
      await api("/tailor/one-off", { method: "DELETE" });
    } else {
      const body = new FormData();
      body.append("file", file);
      const response = await fetch("/api/backend/tailor/one-off", { method: "POST", body });
      if (!response.ok) toast((await response.json().catch(() => ({})))?.detail ?? "That file couldn't be used.");
    }
    reload();
  }

  const header = <PageHeader title="Tailor" description="Review each proposed change against your verified facts. Nothing is used until you decide." />;
  if (error) return <>{header}<ErrorBox error={error} retry={reload} /></>;
  if (loading && !data) return <>{header}<Spinner label="Loading your review" /></>;
  if (!data) return null;

  if (!data.job) {
    return (
      <>
        {header}
        <Card>
          <h2 className="text-[22px] font-semibold">Choose a job first</h2>
          <p className="mt-1 text-muted">Tailoring works against one real posting. Pick a role in Jobs and choose <span className="font-semibold">Prepare this application</span>.</p>
          <LinkButton href="/jobs" variant="primary" className="mt-5">Find a job <ArrowRight aria-hidden className="size-4" /></LinkButton>
        </Card>
        <Card className="mt-6">
          <h2 className="text-[20px] font-semibold">Or paste a job description</h2>
          <p className="mt-1 mb-4 text-muted">For a role you found elsewhere. It&apos;s kept with your jobs, marked as pasted by you.</p>
          <PastedJobForm onDone={set} />
        </Card>
      </>
    );
  }

  if (data.review && !running) {
    return (
      <>
        {header}
        <Context page={data} />
        <ReviewRoom review={data.review} onChange={(r: Review) => set({ ...data, review: r })} onDiscard={discard} />
      </>
    );
  }

  return (
    <>
      {header}
      <Context page={data} />
      {running ? (
        <Card aria-live="polite">
          <div className="flex items-center gap-3">
            <Loader2 aria-hidden className="size-6 animate-spin text-primary" />
            <div>
              <h2 className="text-[20px] font-semibold">Tailoring your resume…</h2>
              <p className="text-muted">{data.run.step ?? "Starting"}…</p>
              <p className="text-[14px] text-muted">Usually about a minute. You can leave this page and come back.</p>
            </div>
          </div>
        </Card>
      ) : data.existing && !redo ? (
        <Card>
          <h2 className="text-[22px] font-semibold">Your tailored resume is ready</h2>
          <p className="mt-1 text-muted">
            Version {data.existing.version} · {data.existing.status === "PASS" ? "passed validation" : "passed with warnings to read"} ·{" "}
            {data.existing.review_complete ? "every change reviewed" : "changes not fully reviewed"}
          </p>
          <div className="mt-5 flex flex-wrap gap-2">
            <LinkButton href="/apply" variant="primary">Continue to application <ArrowRight aria-hidden className="size-4" /></LinkButton>
            <Button onClick={() => setRedo(true)}>Tailor again</Button>
          </div>
          <p className="mt-3 text-[14px] text-muted">The change-by-change review for this version wasn&apos;t saved. Tailor again to review changes one by one.</p>
        </Card>
      ) : (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_320px]">
          <Card>
            <h2 className="text-[22px] font-semibold">Create your tailored resume</h2>
            {data.run.status === "failed" && <div className="mt-3"><Alert tone="blocked" role="alert" title="The last run didn't finish">{data.run.error}</Alert></div>}
            {data.resume ? (
              <p className="mt-2">Using <span className="font-semibold">{data.resume.label}</span></p>
            ) : (
              <div className="mt-3"><Alert tone="review" title="No resume yet">Import your resume in <a className="font-semibold underline" href="/profile">Career Profile</a> first.</Alert></div>
            )}
            {!data.model_ready && <div className="mt-3"><Alert tone="review" title="The writing model isn't set up">Enter your own model and key under Settings, or set LLM_MODEL and LLM_API_KEY on the server.</Alert></div>}
            <details className="mt-5 rounded-[var(--radius-card)] border border-line p-4">
              <summary className="cursor-pointer font-semibold">Settings</summary>
              <div className="mt-4 flex flex-col gap-4">
                <RadioGroup legend="Resume length" name="length" value={length} options={[...LENGTHS]} onChange={setLength} />
                <Checkbox label="Light touch: only add missing keywords, don't rewrite bullets" checked={lightTouch} onChange={setLightTouch} />
                <div>
                  <label htmlFor="one-off" className="text-[15px] font-semibold">Use a different resume file for this job only</label>
                  <input id="one-off" type="file" accept=".docx,.pdf" className="mt-1 block text-[15px]" onChange={(e) => void oneOff(e.target.files?.[0] ?? null)} />
                  {data.resume?.one_off && <Button variant="ghost" className="mt-1" onClick={() => void oneOff(null)}>Use my Career Profile resume instead</Button>}
                </div>
                <fieldset className="flex flex-col gap-3 rounded-[var(--radius-card)] border border-line p-3">
                  <legend className="px-1 text-[15px] font-semibold">Your own model (optional)</legend>
                  <p className="text-[14px] text-muted">Used for this run only. Your key is never stored.</p>
                  <TextField label="Model" placeholder="e.g. gemini/gemini-flash-latest" value={model.model}
                    onChange={(e) => setModel({ ...model, model: e.target.value })} />
                  <TextField label="API key" type="password" autoComplete="off" value={model.api_key}
                    onChange={(e) => setModel({ ...model, api_key: e.target.value })} />
                  {data.custom_api_base_allowed && (
                    <TextField label="API address (local only)" placeholder="Leave empty for the provider's default" value={model.api_base}
                      onChange={(e) => setModel({ ...model, api_base: e.target.value })} />
                  )}
                </fieldset>
              </div>
            </details>
            {startError && <div className="mt-4"><Alert tone="blocked" role="alert">{startError}</Alert></div>}
            <Button variant="primary" className="mt-5" busy={starting} disabled={!data.resume || (!data.model_ready && !(model.model.trim() && model.api_key.trim()))} onClick={start}>
              <Wand2 aria-hidden className="size-4" /> Tailor my resume
            </Button>
          </Card>
          <Card>
            <h2 className="text-[18px] font-semibold">What happens</h2>
            <p className="mt-2 text-muted">Job Copilot rewrites only what your verified facts support, checks every line, and shows each change for you to accept, edit or reject.</p>
            <p className="mt-2 text-muted">Requirements you don&apos;t meet are listed, never added.</p>
          </Card>
        </div>
      )}
    </>
  );
}
