import { ArrowRight } from "lucide-react";
import { audienceSetting } from "../data/audience";
import { categorySet } from "../data/playSets";
import { useSetting } from "../hooks";
import type { Category } from "../types";
import { savedProgress } from "../utils/resume";
import { CategoryIcon } from "./CategoryIcon";
import { ProgressRing } from "./ProgressRing";
import { tintClass } from "./tint";
import { topicSetting } from "./TopicPicker";

/** The whole card is one link into the category's questions. Shows how far through you are, and
 *  counts only the questions that suit the group chosen on the Explore page. On a phone it is a
 *  compact tile (icon, name, count) so the cards fit in a short scroll. */
export function CategoryCard({ category, index = 0, className = "" }: { category: Category; index?: number; className?: string }) {
  const audience = useSetting(audienceSetting);
  const topic = useSetting(topicSetting);
  const set = categorySet(category.id, audience, topic);
  if (!set || set.pool.length === 0) return null;

  const progress = savedProgress(set);
  const inProgress = progress && !progress.finished && progress.done > 0;
  const count = category.id === "trivia" ? "Quiz" : `${set.pool.length} questions`;
  return (
    <a
      href={set.href}
      style={{ animationDelay: `${Math.min(index, 9) * 40}ms` }}
      className={`group flex animate-fade-up flex-col gap-3 rounded-3xl border p-4 shadow-sm transition duration-200 hover:-translate-y-1 hover:shadow-lg focus-visible:-translate-y-1 sm:gap-4 sm:p-5 ${tintClass[category.tint]} ${className}`}
    >
      <div className="flex items-start justify-between gap-3">
        <CategoryIcon category={category} />
        <span className="hidden rounded-full bg-surface/70 px-3 py-1 text-xs font-semibold text-muted sm:inline">{count}</span>
      </div>
      <div>
        <h3 className="text-base font-bold leading-snug sm:text-lg">{category.name}</h3>
        <p className="mt-0.5 text-sm font-semibold text-muted sm:hidden">{count}</p>
        <p className="mt-1 hidden text-[15px] leading-relaxed text-muted sm:block">{category.description}</p>
      </div>
      <div className="mt-auto flex items-center justify-between gap-3">
        <span className="hidden items-center gap-1.5 text-[15px] font-bold text-plum-700 sm:inline-flex dark:text-onplum-soft">
          {inProgress ? "Continue" : "Start"} <ArrowRight aria-hidden className="size-4 transition-transform group-hover:translate-x-1" />
        </span>
        {progress && progress.done > 0 && (
          <span className="flex items-center gap-2 text-sm font-semibold text-muted">
            <ProgressRing done={progress.done} total={progress.total} size={28} />
            {progress.finished ? "Finished" : `${progress.done} of ${progress.total} seen`}
          </span>
        )}
      </div>
    </a>
  );
}
