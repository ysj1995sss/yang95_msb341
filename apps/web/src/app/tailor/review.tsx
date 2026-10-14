"use client";

import { ArrowRight, Check, Circle, Download, Pencil, RotateCcw } from "lucide-react";
import { useState } from "react";
import { Alert, Button, Card, Checkbox, Chip, DownloadLink, LinkButton, TextArea, cx, toneOf, useToast } from "@/components/ui";
import { ApiError, api } from "@/lib/api";
import type { Change, Decision, Review } from "@/lib/types";
import { KeywordReport, ReadabilityCheck, RequirementReview } from "./requirement-review";
import { ResumeSource } from "./resume-source";

const pct = (v: number | null) => (v === null || v === undefined ? "–" : `${Math.round(v * 100)}%`);

const FAILED_CHECK = "We could not verify this claim";

/** A review-list row's state in words: decided (and by whom when AI decided) or not, and a failed check. */
function queueState(c: Change): string {
  const decided = c.decision ? `${c.decision_label}${c.decision_origin === "AI-assisted" ? " by AI assistance" : ""}`
    : c.left_out ? "Left out" : "Not reviewed";
  return c.check === FAILED_CHECK ? `${decided} · failed a check` : decided;
}

function Steps({ review }: { review: Review }) {
  const p = review.progress;
  const allReviewed = p.reviewed === p.total;
  const steps = [
    { label: "Resume built", state: "complete" },
    { label: p.label, state: allReviewed ? "complete" : "current" },
    { label: "Rebuilt with your decisions", state: !p.needs_rebuild && allReviewed ? "complete" : allReviewed ? "current" : "pending" },
    { label: "Ready for Apply", state: p.can_continue ? "complete" : "pending" },
  ];
  return (
    <ol aria-label="Review progress" className="mb-6 grid grid-cols-1 gap-2 sm:grid-cols-4">
      {steps.map((s) => (
        <li key={s.label} className={cx("rounded-[var(--radius-control)] border-t-4 bg-paper px-3 py-2 text-[14px] font-semibold",
          s.state === "complete" ? "border-verified text-verified" : s.state === "current" ? "border-primary text-ink" : "border-line text-muted")}>
          {s.label}<span className="sr-only"> — {s.state}</span>
        </li>
      ))}
    </ol>
  );
}

function ChangeCard({ change, review, onDecide }: {
  change: Change; review: Review; onDecide: (d: Decision, manual?: string) => Promise<void>;
}) {
  const [editing, setEditing] = useState(change.decision === "MANUALLY_EDITED");
  const [text, setText] = useState(change.manual_text);
  const [busy, setBusy] = useState<Decision | null>(null);
  const run = async (d: Decision, manual?: string) => { setBusy(d); try { await onDecide(d, manual); } finally { setBusy(null); } };
  return (
    <Card aria-labelledby={`change-${change.id}`}>
      <p id={`change-${change.id}`} className="break-words text-[15px] font-semibold text-primary">
        {change.title || change.section_label} · {change.decision_label}
      </p>
      <p className="mt-1 text-[14px] text-muted">{change.category.replaceAll("_", " ")} · {change.section_label}</p>
      <ol className="mt-3 grid gap-2 text-[15px] md:grid-cols-3">
        <li className="min-w-0 whitespace-pre-wrap break-words rounded-[var(--radius-control)] bg-canvas p-3"><span className="block text-[13px] text-muted">Job requirement</span><span>{change.full_requirement || change.requirement}</span></li>
        <li className="min-w-0 whitespace-pre-wrap break-words rounded-[var(--radius-control)] bg-canvas p-3"><span className="block text-[13px] text-muted">Supporting fact</span>{change.fact}</li>
        <li className="min-w-0 whitespace-pre-wrap break-words rounded-[var(--radius-control)] bg-canvas p-3"><span className="block text-[13px] text-muted">Resume change</span>{change.reason}</li>
      </ol>
      <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2">
        <div className="min-w-0"><p className="text-[13px] font-semibold text-muted uppercase">Original</p><p className="mt-1 whitespace-pre-wrap break-words">{change.original || "(new line)"}</p></div>
        <div className="min-w-0"><p className="text-[13px] font-semibold text-muted uppercase">Proposed</p><p className="mt-1 whitespace-pre-wrap break-words rounded-[var(--radius-control)] bg-primary-soft p-2">{change.proposed}</p></div>
      </div>
      {!!change.added_skills?.length && (
        <ul className="mt-3 flex flex-col gap-2 text-[14px]" aria-label="Skills added to your skills line">
          {change.added_skills.map((skill) => (
            <li key={skill.term} className="flex flex-wrap items-center gap-2">
              <Chip tone={skill.level === 2 ? "verified" : "review"}>{skill.level === 2 ? "Added skill: you have it" : "Added skill: adjacent"}</Chip>
              <span className="font-semibold">{skill.term}</span>
              <span className="text-muted">{skill.reason}</span>
            </li>
          ))}
        </ul>
      )}
      <p className="mt-2 text-[14px] text-muted">Check: {change.check}</p>
      {change.decision && <p className="mt-1 text-[14px] text-muted"><span>{change.decision_origin === "AI-assisted" ? "Chosen by AI assistance" : change.decision_origin === "person" ? "Chosen by you" : "Origin not recorded"}</span>{change.decision_reason && <span> · {change.decision_reason}</span>}</p>}
      {editing && (
        <div className="mt-4 flex flex-col gap-2">
          <TextArea label="Your wording" help="Only facts already in your Career Profile are allowed." rows={3}
            value={text} onChange={(e) => setText(e.target.value)} />
          <Button variant="primary" className="self-start" busy={busy === "MANUALLY_EDITED"} disabled={!text.trim()}
            onClick={() => run("MANUALLY_EDITED", text)}>Save my wording</Button>
        </div>
      )}
      <div className="mt-4 flex flex-wrap gap-2">
        <Button variant="primary" busy={busy === "ACCEPTED"} onClick={() => { setEditing(false); void run("ACCEPTED"); }}>
          <Check aria-hidden className="size-4" /> {review.verbs.ACCEPTED}
        </Button>
        <Button onClick={() => setEditing(true)} aria-pressed={editing}>
          <Pencil aria-hidden className="size-4" /> {review.verbs.MANUALLY_EDITED}
        </Button>
        <Button busy={busy === "REJECTED"} onClick={() => { setEditing(false); void run("REJECTED"); }}>
          <RotateCcw aria-hidden className="size-4" /> {review.verbs.REJECTED}
        </Button>
      </div>
    </Card>
  );
}

export function ReviewRoom({ review, onChange, onReload, onDiscard }: {
  review: Review; onChange: (r: Review) => void; onReload: () => void; onDiscard: () => void;
}) {
  const toast = useToast();
  const [focus, setFocus] = useState<string | null>(null);
  const [rebuilding, setRebuilding] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showAll, setShowAll] = useState(false);
  const [selected, setSelected] = useState<string[]>([]);
  const [batchBusy, setBatchBusy] = useState(false);
  const current = review.changes.find((c) => c.id === focus) ?? review.changes.find((c) => c.id === review.next_undecided) ?? review.changes[0];
  const p = review.progress;
  const selectedIds = selected.filter((id) => review.changes.some((change) => change.id === id));

  function handleError(cause: unknown) {
    if (cause instanceof ApiError && cause.status === 409) {
      setSelected([]);
      onReload();
      setError("This review changed elsewhere. The latest decisions are loading; select changes again.");
    } else {
      setError((cause as Error).message);
    }
  }

  async function decideSelected(decision: "ACCEPTED" | "REJECTED") {
    if (!selectedIds.length) return;
    setBatchBusy(true);
    setError(null);
    try {
      const next = await api<Review>("/tailor/decisions/batch", { method: "POST", json: {
        expected_revision: review.review_revision,
        decisions: selectedIds.map((change_id) => ({ change_id, decision })),
      } });
      onChange(next);
      setSelected([]);
      toast(`${selectedIds.length} ${selectedIds.length === 1 ? "change" : "changes"} ${decision === "ACCEPTED" ? "accepted" : "kept original"}.`);
    } catch (cause) {
      handleError(cause);
    } finally {
      setBatchBusy(false);
    }
  }

  async function decide(change: Change, decision: Decision, manual?: string) {
    setError(null);
    try {
      const next = await api<Review>("/tailor/decisions", { method: "POST", json: { change_id: change.id, decision, manual_text: manual ?? null, expected_revision: review.review_revision } });
      onChange(next);
      if (decision !== "MANUALLY_EDITED" || manual !== undefined) {
        const label = { ACCEPTED: "Accepted", MANUALLY_EDITED: "Edit saved", REJECTED: "Original kept" }[decision];
        toast(`${label}.`);
        const after = next.changes.findIndex((c) => c.id === change.id);
        const nextOpen = next.changes.slice(after + 1).find((c) => !c.decision) ?? next.changes.find((c) => !c.decision);
        setFocus(nextOpen?.id ?? change.id);
      }
    } catch (e) {
      handleError(e);
    }
  }

  async function rebuild() {
    setRebuilding(true);
    setError(null);
    try {
      onChange(await api<Review>("/tailor/rebuild", { method: "POST" }));
      toast("Resume rebuilt with your decisions.");
    } catch (e) {
      handleError(e);
    } finally {
      setRebuilding(false);
    }
  }

  return (
    <>
      <Steps review={review} />
      <ResumeSource info={review.source_info} />
      {review.sync_summary && <div className="mb-4"><Alert tone="primary">{review.sync_summary}</Alert></div>}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,1.15fr)_minmax(0,0.85fr)]">
        <div className="flex min-w-0 flex-col gap-5">
          <h2 className="text-[22px] font-semibold">Proposed changes</h2>
          {review.assisted_note && <Alert tone="review" title="AI assistance didn't decide anything" role="status">{review.assisted_note}</Alert>}
          {review.skills_note && <Alert tone="review" title="Some added skills were left out" role="status">{review.skills_note}</Alert>}
          <p className="text-[14px] text-muted">{review.review_mode === "assisted" ? "AI assistance made only conservative decisions; review them and decide any remaining changes." : "Review each change yourself."} Select several changes to decide them together, or open one to edit its wording.</p>
          {review.changes.length > 0 ? (
            <>
              <div className="flex flex-wrap items-center gap-2">
                <Button onClick={() => setShowAll((value) => !value)}>{showAll ? "Show one change" : "Show all changes"}</Button>
                {/* Changes that failed a check can't be accepted, so they're never swept into a batch accept. */}
                <Button onClick={() => setSelected(review.changes.filter((change) => !change.decision && change.check !== FAILED_CHECK).map((change) => change.id))}>Select all unreviewed</Button>
                <Button onClick={() => setSelected([])} disabled={!selectedIds.length}>Clear selection</Button>
                <span role="status" className="text-[14px] font-semibold">{selectedIds.length} selected</span>
              </div>
              <div className="flex flex-wrap gap-2">
                <Button variant="primary" busy={batchBusy} disabled={!selectedIds.length || batchBusy} onClick={() => void decideSelected("ACCEPTED")}>Accept selected</Button>
                <Button busy={batchBusy} disabled={!selectedIds.length || batchBusy} onClick={() => void decideSelected("REJECTED")}>Keep original for selected</Button>
              </div>
              <nav aria-label="Review queue">
                <ol className="flex flex-col gap-1">
                  {review.changes.map((c, i) => (
                    <li key={c.id} className="flex min-w-0 items-start gap-2">
                      <Checkbox label={`Select ${c.title || `${i + 1}. ${c.section_label}`}`} hideLabel checked={selectedIds.includes(c.id)}
                        onChange={(checked) => setSelected((ids) => checked ? [...ids, c.id] : ids.filter((id) => id !== c.id))} />
                      <button type="button" aria-current={c.id === current?.id ? "step" : undefined} onClick={() => setFocus(c.id)}
                        className={cx("flex min-h-11 min-w-0 flex-1 items-start gap-2 rounded-[var(--radius-control)] px-3 py-2 text-left text-[15px] transition-colors duration-150 cursor-pointer",
                          c.id === current?.id ? "bg-primary-soft font-semibold text-primary" : "hover:bg-paper")}>
                        {c.decision ? <Check aria-hidden className="size-4 shrink-0 text-verified" /> : <Circle aria-hidden className="size-4 shrink-0 text-line-strong" />}
                        <span className="min-w-0 whitespace-normal break-words">
                          {c.title || `${i + 1}. ${c.section_label}: ${c.original || "(new line)"} → ${c.proposed}`}
                          {/* Spec 019: the state in words, not only by icon and color. */}
                          <span className="block text-[13px] font-normal text-muted">{queueState(c)}</span>
                        </span>
                      </button>
                    </li>
                  ))}
                </ol>
              </nav>
              {showAll ? (
                <div className="flex flex-col gap-4">{review.changes.map((change) => (
                  <ChangeCard key={change.id} change={change} review={review} onDecide={(d, m) => decide(change, d, m)} />
                ))}</div>
              ) : current && <ChangeCard key={current.id} change={current} review={review} onDecide={(d, m) => decide(current, d, m)} />}
            </>
          ) : <Alert tone="primary">{review.empty_message}</Alert>}

          {review.turned_down.length > 0 && (
            <details className="rounded-[var(--radius-card)] border border-line bg-paper p-4">
              <summary className="cursor-pointer font-semibold">Turned down by our checks ({review.turned_down.length})</summary>
              <p className="mt-2 text-[14px] text-muted">These proposals were not used. Your original wording stays.</p>
              <ul className="mt-2 list-disc pl-5">{review.turned_down.map((t) => <li key={t.original}><span className="font-semibold">{t.original.slice(0, 90)}</span> — {t.reason}</li>)}</ul>
            </details>
          )}

          {review.keyword_report && <KeywordReport report={review.keyword_report} onJump={(id) => { setFocus(id); window.scrollTo({ top: 0, behavior: "smooth" }); }} />}
          {review.requirement_review && <RequirementReview review={review.requirement_review} />}

          {(review.true_gaps.length > 0 || review.blocked.length > 0) && (
            <section aria-labelledby="missing">
              <h3 id="missing" className="text-[18px] font-semibold">Missing, never added</h3>
              <div className="mt-2"><Alert tone="blocked">These requirements aren&apos;t in your verified experience. Job Copilot will not add them.</Alert></div>
              <ul className="mt-3 list-disc pl-5">
                {review.true_gaps.map((g) => <li key={g.full} title={g.full !== g.label ? g.full : undefined}>{g.label}</li>)}
                {review.blocked.map((b) => <li key={b}>Blocked a proposed line that claimed <em>{b}</em>; the original was kept.</li>)}
              </ul>
            </section>
          )}
        </div>

        <aside aria-labelledby="preview" className="flex min-w-0 flex-col gap-4 lg:sticky lg:top-20 lg:self-start">
          <h2 id="preview" className="text-[22px] font-semibold">Resume preview</h2>
          <div className="flex flex-wrap gap-2">
            <Chip tone={toneOf(review.status_tone)}>{review.status_text}</Chip>
            <Chip>{review.page_count ? `${review.page_count} page(s)` : "Page count not checked"}</Chip>
            <Chip>{`Version ${review.version}`}</Chip>
            <Chip>{review.fidelity}</Chip>
          </div>
          {review.status === "FAIL" && <Alert tone="blocked" role="alert">This resume failed validation and can&apos;t be downloaded or used to apply.</Alert>}
          {review.status === "WARNING" && <Alert tone="review" title="Passed with warnings. Read them before you use this resume." />}
          {review.status !== "PASS" && review.findings.length > 0 && <ul className="list-disc pl-5 text-[15px]">{review.findings.map((f, i) => <li key={`${i}-${f}`}>{f}</li>)}</ul>}
          <ReadabilityCheck readability={review.readability} />
          {review.preview_pages > 0 ? (
            <div className="flex max-h-[70vh] flex-col gap-3 overflow-y-auto rounded-[var(--radius-card)] border border-line bg-canvas p-3">
              {Array.from({ length: review.preview_pages }, (_, i) => (
                // eslint-disable-next-line @next/next/no-img-element -- generated per version, not a static asset
                <img key={i} src={`/api/backend/tailor/preview/${i + 1}?v=${review.version}`} alt={`Tailored resume, page ${i + 1}`}
                  className="w-full rounded-[var(--radius-control)] border border-line bg-white" />
              ))}
            </div>
          ) : (
            <TextArea label="Resume text" readOnly rows={16} value={review.tailored_text} />
          )}
          {review.status !== "FAIL" && (
            <div className="flex flex-wrap gap-2">
              {review.has_pdf && <DownloadLink href="/api/backend/tailor/download/pdf"><Download aria-hidden className="size-4" /> Download PDF</DownloadLink>}
              {review.has_docx && <DownloadLink href="/api/backend/tailor/download/docx"><Download aria-hidden className="size-4" /> Download Word</DownloadLink>}
            </div>
          )}
          <details className="rounded-[var(--radius-card)] border border-line bg-paper p-4 text-[15px]">
            <summary className="cursor-pointer font-semibold">Details</summary>
            <p className="mt-2">Pages: {review.pages_before_after[0] ?? "–"} before, {review.pages_before_after[1] ?? "–"} after.</p>
            <p>Keyword overlap: {pct(review.alignment.before)} before, {pct(review.alignment.after)} after.</p>
            <p className="text-[14px] text-muted">{review.overlap_note}</p>
            {review.unsupported_claims.length > 0 && (<><p className="mt-2 font-semibold">Unsupported claims found and blocked:</p><ul className="list-disc pl-5">{review.unsupported_claims.map((c) => <li key={c}>{c}</li>)}</ul></>)}
          </details>
          <details className="text-[15px]">
            <summary className="cursor-pointer text-muted">Start over for this job</summary>
            <p className="mt-2 text-muted">Discards this review, including your decisions and your own wording. Your Career Profile is not changed.</p>
            <Button variant="danger" className="mt-2" onClick={onDiscard}>Discard and tailor again</Button>
          </details>
        </aside>
      </div>

      {/* Pinned from tablet width up. On a phone its stacked text and buttons covered a third of the
          screen (risk check, 2026-10-13), so there it sits after the review; the steps above show progress. */}
      <div className="z-30 mt-8 flex flex-col gap-3 rounded-[var(--radius-card)] border border-line bg-paper p-4 sm:sticky sm:bottom-16 sm:flex-row sm:items-center sm:justify-between md:bottom-4">
        <div role="status">
          <p className="font-semibold">{p.label}</p>
          <p className="text-[14px] text-muted">{p.blocker || "Your resume is ready for Apply."}</p>
          {error && <p role="alert" className="text-[14px] font-semibold text-blocked">{error}</p>}
        </div>
        <div className="flex flex-wrap gap-2">
          <Button busy={rebuilding} disabled={!p.needs_rebuild} onClick={rebuild} title="Rebuild the resume with your decisions. The model is not run again.">
            Rebuild resume
          </Button>
          {p.can_continue
            ? <LinkButton href="/apply" variant="primary">Continue to application <ArrowRight aria-hidden className="size-4" /></LinkButton>
            : <Button variant="primary" disabled title={p.blocker}>Continue to application</Button>}
        </div>
      </div>
    </>
  );
}
