import { Eye, Sun } from "lucide-react";
import { useMemo, useState } from "react";
import { dailyQuestions } from "../data/dailyQuestions";
import { dailyFor } from "../utils/daily";
import { loadDailyRevealed, saveDailyRevealed } from "../utils/storage";

/** Today's question: the same all day (by the local date). Read it, talk about it, come back tomorrow. */
export function DailyQuestion() {
  const { question, dateKey } = useMemo(() => dailyFor(new Date(), dailyQuestions), []);
  const [revealed, setRevealed] = useState(() => loadDailyRevealed(dateKey));
  const today = new Date().toLocaleDateString(undefined, { weekday: "long", month: "long", day: "numeric" });

  function reveal() {
    setRevealed(true);
    saveDailyRevealed(dateKey);
  }

  return (
    <section aria-labelledby="daily-heading" className="relative overflow-hidden rounded-[2rem] bg-gradient-to-br from-[#3b2690] via-plum-700 to-plum-600 p-6 text-cream shadow-xl sm:p-10">
      {/* Coral only as a glow in the corner: cream text on coral would be too faint to read. */}
      <div aria-hidden className="pointer-events-none absolute -right-20 -top-20 size-64 rounded-full bg-coral-500/45 blur-3xl" />
      <div aria-hidden className="pointer-events-none absolute -bottom-24 left-1/3 size-56 rounded-full bg-plum-400/30 blur-3xl" />
      <div className="relative flex flex-wrap items-center gap-3">
        <span className="inline-flex items-center gap-2 rounded-full bg-white/15 px-3 py-1 text-sm font-semibold">
          <Sun aria-hidden className="size-4" /> Question of the Day
        </span>
        <span className="text-sm text-onplum">{today}</span>
      </div>
      <h2 id="daily-heading" className="sr-only">Question of the Day</h2>

      {!revealed ? (
        <div className="relative mt-6">
          <p className="max-w-xl text-lg text-onplum">A new question every day. Answer it alone, or ask the person next to you.</p>
          <button type="button" onClick={reveal}
            className="mt-6 inline-flex min-h-12 cursor-pointer items-center gap-2 rounded-full bg-cream px-6 font-bold text-plum-900 shadow-md transition hover:bg-white">
            <Eye aria-hidden className="size-5" /> Reveal today's question
          </button>
        </div>
      ) : (
        <div className="relative mt-6 animate-fade-up">
          <p className="max-w-3xl text-2xl font-extrabold leading-snug sm:text-3xl">{question.text}</p>
          <p className="mt-5 text-onplum">Read it out loud and talk it over. A new question arrives tomorrow.</p>
        </div>
      )}
    </section>
  );
}
