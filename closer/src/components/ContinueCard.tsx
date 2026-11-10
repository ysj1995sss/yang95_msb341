import { ArrowRight, Play } from "lucide-react";
import { useMemo } from "react";
import { setFromKey } from "../data/playSets";
import { customQuestions } from "../utils/custom";
import { loadLastPlayed, savedProgress } from "../utils/resume";
import { ProgressRing } from "./ProgressRing";

/** "Continue where you left off": the last set played, if its round isn't finished. */
export function ContinueCard() {
  const last = useMemo(() => {
    const key = loadLastPlayed();
    const set = key ? setFromKey(key, customQuestions.get()) : null;
    const progress = set ? savedProgress(set) : null;
    return set && progress && !progress.finished && progress.done > 0 ? { set, progress } : null;
  }, []);
  if (!last) return null;
  const { set, progress } = last;
  return (
    <a href={set.href}
      className="group flex items-center gap-4 rounded-3xl border border-plum-200 bg-surface p-4 shadow-sm transition hover:-translate-y-0.5 hover:border-plum-300 hover:shadow-lg sm:p-5">
      <span aria-hidden className="inline-flex size-12 shrink-0 items-center justify-center rounded-2xl bg-plum-600 text-white">
        <Play className="size-5" fill="currentColor" />
      </span>
      <span className="min-w-0 flex-1">
        <span className="block text-sm font-bold text-muted">Continue where you left off</span>
        <span className="block truncate text-lg font-extrabold">{set.title}</span>
        <span className="block text-[15px] text-muted">{progress.done} of {progress.total} seen</span>
      </span>
      <ProgressRing done={progress.done} total={progress.total} size={44} />
      <ArrowRight aria-hidden className="size-5 shrink-0 text-plum-600 transition-transform group-hover:translate-x-1 dark:text-onplum-soft" />
    </a>
  );
}
