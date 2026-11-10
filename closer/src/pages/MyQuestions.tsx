import { PenLine, Play, Plus, Trash2 } from "lucide-react";
import { useId, useMemo, useState } from "react";
import { DepthMeter } from "../components/DepthSelector";
import { primary, secondary } from "../components/ui";
import { conversationLevels, DEPTHS } from "../data/depth";
import { mineSet } from "../data/playSets";
import { useCustomQuestions } from "../hooks";
import type { Depth } from "../types";
import { customQuestions, MAX_CUSTOM, MAX_LENGTH } from "../utils/custom";
import { href } from "../utils/router";
import { SetPlay } from "./SetPlay";

/** My questions: write your own, keep them on this device, and play them like any other set. */
export function MyQuestions() {
  const mine = useCustomQuestions();
  const [text, setText] = useState("");
  const [depth, setDepth] = useState<Depth>(1);
  const [error, setError] = useState("");
  const [added, setAdded] = useState("");
  const id = useId();

  function add(e: React.FormEvent) {
    e.preventDefault();
    const result = customQuestions.add(text, depth);
    if (result.ok) {
      setText("");
      setError("");
      setAdded(`Added: ${result.question.text}`);
    } else {
      setAdded("");
      setError(result.reason);
    }
  }

  const field = "mt-2 w-full rounded-2xl border border-plum-100 bg-page/60 p-3.5 text-[16px] placeholder:text-muted/80 focus-visible:border-plum-400";
  return (
    <div className="mx-auto max-w-3xl px-4 pt-12 sm:px-6">
      <div className="flex items-center gap-4">
        <span aria-hidden className="inline-flex size-16 shrink-0 items-center justify-center rounded-3xl bg-gradient-to-br from-sky-400 to-plum-600 text-white shadow-md">
          <PenLine className="size-8" />
        </span>
        <div>
          <h1 tabIndex={-1} className="text-3xl font-extrabold tracking-tight sm:text-4xl">My questions</h1>
          <p className="mt-1 text-muted">Write questions for your own group. They stay on this device.</p>
        </div>
      </div>

      <form onSubmit={add} className="mt-8 rounded-[2rem] border border-plum-100 bg-surface p-6 shadow-lg sm:p-8">
        <label htmlFor={`${id}-text`} className="text-sm font-semibold text-muted">Your question</label>
        <textarea id={`${id}-text`} rows={3} value={text} maxLength={MAX_LENGTH + 50}
          onChange={(e) => { setText(e.target.value); setError(""); setAdded(""); }}
          placeholder="What's a memory that always makes you laugh?"
          aria-describedby={`${id}-help`} aria-invalid={error ? true : undefined}
          className={field} />
        <p id={`${id}-help`} className={`mt-1 text-right text-xs font-semibold ${text.trim().length > MAX_LENGTH ? "text-coral-700" : "text-muted"}`}>
          {text.trim().length} / {MAX_LENGTH}
        </p>

        <div className="mt-3 grid gap-4 sm:grid-cols-[1fr_auto] sm:items-end">
          <div>
            <label htmlFor={`${id}-level`} className="text-sm font-semibold text-muted">How deep does it go?</label>
            <select id={`${id}-level`} value={depth} onChange={(e) => setDepth(Number(e.target.value) as Depth)} className={field}>
              {DEPTHS.map((d) => <option key={d} value={d}>{conversationLevels[d].name}: {conversationLevels[d].hint}</option>)}
            </select>
          </div>
          <button type="submit" className={primary}><Plus aria-hidden className="size-5" /> Add question</button>
        </div>

        <p role="alert" className="mt-3 min-h-6 text-sm font-semibold text-coral-700">{error}</p>
        <p role="status" className="min-h-5 text-sm font-semibold text-plum-700 dark:text-onplum-soft">{added}</p>
      </form>

      <section aria-labelledby={`${id}-list`} className="mt-10">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 id={`${id}-list`} className="text-xl font-extrabold">Your questions <span className="text-base font-semibold text-muted">({mine.length} of {MAX_CUSTOM})</span></h2>
          {mine.length > 0 && (
            <a href={href.minePlay} className={primary}><Play aria-hidden className="size-5" /> Play my questions</a>
          )}
        </div>

        {mine.length === 0 ? (
          <div className="mt-4 rounded-[2rem] border border-dashed border-plum-200 bg-surface/70 p-8 text-center">
            <h3 className="text-lg font-extrabold">No questions yet</h3>
            <p className="mx-auto mt-1 max-w-md text-muted">Add your first one above. It could be an inside joke, a family tradition, or something you've always wanted to ask.</p>
          </div>
        ) : (
          <ul className="mt-4 space-y-3">
            {mine.map((q) => (
              <li key={q.id} className="flex items-start justify-between gap-3 rounded-2xl border border-plum-100 bg-surface p-4 pl-5 shadow-sm">
                <div>
                  <p className="text-[17px] font-bold leading-snug">{q.text}</p>
                  <p className="mt-2 flex items-center gap-2 text-sm font-semibold text-muted">
                    <DepthMeter depth={q.depth} /> {conversationLevels[q.depth].name}
                  </p>
                </div>
                <button type="button" aria-label={`Delete: ${q.text}`}
                  onClick={() => { if (window.confirm("Delete this question?")) customQuestions.remove(q.id); }}
                  className="inline-flex size-11 shrink-0 cursor-pointer items-center justify-center rounded-full text-muted transition hover:bg-coral-50 hover:text-coral-700">
                  <Trash2 aria-hidden className="size-5" />
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

export function MinePlay() {
  const mine = useCustomQuestions();
  const set = useMemo(() => mineSet(mine), [mine]);
  if (set.pool.length === 0) {
    return (
      <div className="mx-auto max-w-3xl px-4 pt-16 sm:px-6">
        <h1 tabIndex={-1} className="text-3xl font-extrabold">Nothing to play yet</h1>
        <p className="mt-3 text-muted">Write a few questions of your own, then come back to play them.</p>
        <a href={href.mine} className={`${secondary} mt-6`}>Write a question</a>
      </div>
    );
  }
  return (
    <SetPlay set={set} backHref={href.mine} backLabel="Back to my questions"
      icon={
        <span aria-hidden className="inline-flex size-16 shrink-0 items-center justify-center rounded-3xl bg-gradient-to-br from-sky-400 to-plum-600 text-white shadow-md">
          <PenLine className="size-8" />
        </span>
      } />
  );
}
