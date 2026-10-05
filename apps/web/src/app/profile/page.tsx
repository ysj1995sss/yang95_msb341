"use client";

import { X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { ResumeUpload } from "@/components/resume-upload";
import { YourData } from "@/components/your-data";
import { Alert, Button, Card, Chip, ErrorBox, PageHeader, Spinner, cx, toneOf, useToast } from "@/components/ui";
import { api, useResource } from "@/lib/api";
import type { ProfileResponse } from "@/lib/types";
import { EDITORS } from "./editors";

export default function ProfilePage() {
  const toast = useToast();
  const { data, error, loading, reload, set } = useResource<ProfileResponse>("/profile");
  const me = useResource<{ signed_in: boolean }>("/me");
  // undefined: not chosen yet, so the first section needing a look opens (as on the Streamlit page).
  const [chosen, setOpen] = useState<string | null | undefined>(undefined);
  const [confirming, setConfirming] = useState(false);
  const editorRef = useRef<HTMLHeadingElement>(null);

  const open = chosen === undefined ? (data?.first_to_review ?? null) : chosen;
  useEffect(() => {
    if (open) editorRef.current?.focus();
  }, [open]);

  if (error) return <ErrorBox error={error} retry={reload} />;
  if (loading && !data) return <Spinner label="Loading your Career Profile" />;
  if (!data) return null;

  const header = (
    <PageHeader title="Career Profile"
      description="Your verified facts, entered once and reused everywhere. Only what you've confirmed is used." />
  );

  if (!data.readiness.has_resume) {
    return (
      <>
        {header}
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_320px]">
          <Card>
            <h2 className="text-[22px] font-semibold">Import your resume</h2>
            <p className="mb-5 text-muted">Job Copilot reads it once and fills in your profile. You&apos;ll only fix what it got wrong.</p>
            <ResumeUpload onImported={set} />
          </Card>
          <Card>
            <h2 className="text-[18px] font-semibold">What a Career Profile holds</h2>
            <p className="mt-2 text-muted">Contact details, work history, education, skills, links, job goals, work
              authorization, and answers you&apos;ve approved.</p>
          </Card>
        </div>
      </>
    );
  }

  async function confirmRest() {
    setConfirming(true);
    try {
      const result = await api<ProfileResponse & { confirmed: number }>("/profile/confirm", { method: "POST" });
      set(result);
      toast(`Confirmed ${result.confirmed} facts.`);
    } catch (e) {
      toast((e as Error).message);
    } finally {
      setConfirming(false);
    }
  }

  const row = data.rows.find((r) => r.key === open);
  const Editor = open ? EDITORS[open] : null;
  const uploaded = data.resume?.uploaded_at ? new Date(data.resume.uploaded_at).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" }) : "";

  return (
    <>
      {header}
      {data.readiness.facts_confirmed && data.attention.length === 0 ? (
        <Alert tone="verified" title="Your facts are confirmed.">Only these facts are used when Job Copilot tailors a resume.</Alert>
      ) : (
        <Card className="mb-6" aria-labelledby="attention">
          <h2 id="attention" className="text-[18px] font-semibold">
            {data.attention.length
              ? `Needs your attention · ${data.attention.length} ${data.attention.length === 1 ? "item" : "items"} to review`
              : "Nothing looks wrong"}
          </h2>
          {data.attention.length > 0 ? (
            <ul className="mt-2 list-disc pl-5">{data.attention.slice(0, 6).map((i) => <li key={i}>{i}</li>)}</ul>
          ) : (
            <p className="mt-1 text-muted">Give your sections a quick look, then confirm them.</p>
          )}
          {!data.readiness.facts_confirmed && (
            <Button variant="primary" className="mt-4" busy={confirming} onClick={confirmRest}>Confirm the rest</Button>
          )}
        </Card>
      )}

      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.35fr)]">
        <div className="flex flex-col gap-4">
          <Card className="p-0 sm:p-0" aria-labelledby="sections">
            <h2 id="sections" className="sr-only">Sections</h2>
            <ul className="divide-y divide-line">
              {data.rows.map((r) => (
                <li key={r.key} className={cx("flex items-center gap-3 px-4 py-3", r.key === open && "bg-primary-soft")}>
                  <div className="min-w-0 flex-1">
                    <p className="font-semibold">{r.name}</p>
                    <p className="truncate text-[14px] text-muted">{r.detail}</p>
                  </div>
                  <Chip tone={toneOf(r.tone)}>{r.status}</Chip>
                  <Button variant={r.key === open ? "primary" : "secondary"} aria-expanded={r.key === open}
                    aria-controls="section-editor" onClick={() => setOpen(r.key)}>
                    {r.action}<span className="sr-only"> {r.name}</span>
                  </Button>
                </li>
              ))}
            </ul>
          </Card>
          <details className="rounded-[var(--radius-card)] border border-line bg-paper p-4">
            <summary className="cursor-pointer font-semibold">
              Resume source · {data.resume?.filename ?? "none"} · version {data.resume?.version ?? "–"}
            </summary>
            <p className="mt-2 mb-4 text-[14px] text-muted">
              Imported {uploaded}. {data.resume_versions} {data.resume_versions === 1 ? "version" : "versions"} kept;
              earlier versions are never overwritten. Your goals, links and answers are kept when you replace it;
              facts are re-read and need a quick confirmation.
            </p>
            <ResumeUpload onImported={(p) => { set(p); setOpen(p.first_to_review); }}
              label="Replace with a newer resume (Word or PDF)" cta="Replace resume" />
          </details>
        </div>

        <div id="section-editor">
          {row && Editor ? (
            <Card aria-labelledby="editor-title">
              <div className="mb-4 flex items-start justify-between gap-3">
                <div>
                  <h2 id="editor-title" ref={editorRef} tabIndex={-1} className="text-[22px] font-semibold">{row.name}</h2>
                  <p className="text-[14px] text-muted">{data.provenance[row.key] || row.detail}</p>
                </div>
                <Button variant="ghost" onClick={() => setOpen(null)} aria-label={`Close ${row.name}`}>
                  <X aria-hidden className="size-5" />
                </Button>
              </div>
              {row.issues.map((issue) => <div key={issue} className="mb-3"><Alert tone="review">{issue}</Alert></div>)}
              <Editor key={`${row.key}-${data.resume?.version}`} data={data}
                onSaved={(p) => { setOpen(row.key); set(p); }} />
            </Card>
          ) : (
            <Card>
              <h2 className="text-[18px] font-semibold">Choose a section</h2>
              <p className="mt-2 text-muted">Pick Edit, Review or Add. One section opens here at a time.</p>
              <p className="mt-2 text-muted">Everything under &ldquo;Needs your attention&rdquo; is worth a look before you tailor a resume.</p>
            </Card>
          )}
        </div>
      </div>
      <YourData signedIn={Boolean(me.data?.signed_in)} />
    </>
  );
}
