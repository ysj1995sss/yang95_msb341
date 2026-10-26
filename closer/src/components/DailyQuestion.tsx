import { Check, Eye, Sun } from "lucide-react";
import { useId, useMemo, useState } from "react";
import { dailyQuestions } from "../data/dailyQuestions";
import { dailyFor } from "../utils/daily";
import { loadDailyAnswer, saveDailyAnswer } from "../utils/storage";

/** Today's question: the same all day (by the local date), with an optional answer kept in this browser. */
export function DailyQuestion() {
  const { question, dateKey } = useMemo(() => dailyFor(new Date(), dailyQuestions), []);
  const saved = useMemo(() => loadDailyAnswer(dateKey), [dateKey]);
  const [revealed, setRevealed] = useState(Boolean(saved));
  const [text, setText] = useState(saved?.questionId === question.id ? saved.text : "");
  const [status, setStatus] = useState<"idle" | "saved" | "failed">(saved ? "saved" : "idle");
  const fieldId = useId();
  const today = new Date().toLocaleDateString(undefined, { weekday: "long", month: "long", day: "numeric" });

  function save() {
    setStatus(saveDailyAnswer(dateKey, question.id, text.trim()) ? "saved" : "failed");
  }

  return (
    <section aria-labelledby="daily-heading" className="relative overflow-hidden rounded-[2rem] bg-gradient-to-br from-plum-800 via-plum-700 to-plum-600 p-6 text-cream shadow-xl sm:p-10">
      {/* Coral only as a glow in the corner: cream text on coral would be too faint to read. */}
      <div aria-hidden className="pointer-events-none absolute -right-20 -top-20 size-64 rounded-full bg-coral-500/45 blur-3xl" />
      <div aria-hidden className="pointer-events-none absolute -bottom-24 left-1/3 size-56 rounded-full bg-plum-400/30 blur-3xl" />
      <div className="relative flex flex-wrap items-center gap-3">
        <span className="inline-flex items-center gap-2 rounded-full bg-white/15 px-3 py-1 text-sm font-semibold">
          <Sun aria-hidden className="size-4" /> Question of the Day
        </span>
        <span className="text-sm text-plum-100">{today}</span>
      </div>
      <h2 id="daily-heading" className="sr-only">Question of the Day</h2>

      {!revealed ? (
        <div className="relative mt-6">
          <p className="max-w-xl text-lg text-plum-50">A new question every day. Answer it alone, or ask the person next to you.</p>
          <button type="button" onClick={() => setRevealed(true)}
            className="mt-6 inline-flex min-h-12 cursor-pointer items-center gap-2 rounded-full bg-cream px-6 font-bold text-plum-800 shadow-md transition hover:bg-white">
            <Eye aria-hidden className="size-5" /> Reveal today's question
          </button>
        </div>
      ) : (
        <div className="relative mt-6 animate-fade-up">
          <p className="max-w-3xl text-2xl font-extrabold leading-snug sm:text-3xl">{question.text}</p>
          <label htmlFor={fieldId} className="mt-6 block text-sm font-semibold text-plum-50">Your answer (optional)</label>
          <textarea id={fieldId} rows={3} value={text} maxLength={1000}
            onChange={(e) => { setText(e.target.value); setStatus("idle"); }}
            placeholder="Write a few words, or just think about it…"
            className="mt-2 w-full resize-y rounded-2xl border-0 bg-white/95 p-4 text-[16px] text-ink placeholder:text-muted focus-visible:outline-cream" />
          <div className="mt-4 flex flex-wrap items-center gap-3">
            <button type="button" onClick={save} disabled={!text.trim()}
              className="inline-flex min-h-12 cursor-pointer items-center gap-2 rounded-full bg-cream px-6 font-bold text-plum-800 shadow-md transition hover:bg-white disabled:cursor-not-allowed disabled:opacity-60">
              Save answer
            </button>
            <p role="status" className="text-sm font-semibold text-plum-50">
              {status === "saved" && <span className="inline-flex items-center gap-1"><Check aria-hidden className="size-4" /> Saved on this device for today.</span>}
              {status === "failed" && "Your browser isn't letting this page save. Your answer stays here until you leave."}
            </p>
          </div>
        </div>
      )}
    </section>
  );
}
