import { Eye, Sun } from "lucide-react";
import { useMemo, useState } from "react";
import { dailyQuestions } from "../data/dailyQuestions";
import { dailyFor } from "../utils/daily";
import { loadDailyRevealed, saveDailyRevealed } from "../utils/storage";
import { primary } from "./ui";

/** Today's question: the same all day (by the local date). Read it, talk about it, come back tomorrow.
 *  A quiet panel, not a banner: the ten experiences below it should be the loudest thing on the page. */
export function DailyQuestion() {
  const { question, dateKey } = useMemo(() => dailyFor(new Date(), dailyQuestions), []);
  const [revealed, setRevealed] = useState(() => loadDailyRevealed(dateKey));
  const today = new Date().toLocaleDateString(undefined, { weekday: "long", month: "long", day: "numeric" });

  function reveal() {
    setRevealed(true);
    saveDailyRevealed(dateKey);
  }

  return (
    <section aria-labelledby="daily-heading" className="rounded-3xl border border-plum-200 bg-plum-50 p-5 sm:p-7">
      <div className="flex flex-wrap items-center gap-3">
        <span aria-hidden className="inline-flex size-9 items-center justify-center rounded-xl bg-plum-600 text-white">
          <Sun className="size-5" />
        </span>
        <h2 id="daily-heading" className="font-extrabold">Question of the Day</h2>
        <span className="text-sm text-muted">{today}</span>
      </div>

      {!revealed ? (
        <div className="mt-4 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <p className="max-w-xl text-lg text-muted">A new question every day. Answer it alone, or ask the person next to you.</p>
          <button type="button" onClick={reveal} className={`${primary} shrink-0`}>
            <Eye aria-hidden className="size-5" /> Reveal today's question
          </button>
        </div>
      ) : (
        <div className="mt-4 animate-fade-up">
          <p className="max-w-3xl text-2xl font-extrabold leading-snug text-ink sm:text-3xl">{question.text}</p>
          <p className="mt-3 text-muted">Read it out loud and talk it over. A new question arrives tomorrow.</p>
        </div>
      )}
    </section>
  );
}
