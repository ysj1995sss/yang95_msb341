import { useMemo } from "react";
import { TopicPicker, topicSetting } from "../components/TopicPicker";
import { primary } from "../components/ui";
import { AUDIENCES, audienceSetting } from "../data/audience";
import { categorySet } from "../data/playSets";
import { useSetting } from "../hooks";
import { href } from "../utils/router";
import { SetPlay } from "./SetPlay";

export function QuestionExperience({ categoryId }: { categoryId: string }) {
  const audience = useSetting(audienceSetting);
  const topic = useSetting(topicSetting);
  const set = useMemo(() => categorySet(categoryId, audience, topic), [categoryId, audience, topic]);

  if (!set) {
    return (
      <div className="mx-auto max-w-3xl px-4 pt-16 sm:px-6">
        <h1 tabIndex={-1} className="text-3xl font-extrabold">We couldn't find that experience</h1>
        <p className="mt-3 text-muted">It may have moved. Pick one of the ten experiences instead.</p>
        <a href={href.explore} className={`${primary} mt-6`}>See all experiences</a>
      </div>
    );
  }

  const group = AUDIENCES.find((a) => a.id === audience);
  if (set.pool.length === 0) {
    return (
      <div className="mx-auto max-w-3xl px-4 pt-16 sm:px-6">
        <h1 tabIndex={-1} className="text-3xl font-extrabold">{set.title}</h1>
        <p className="mt-3 text-muted">
          There aren't any {set.title} questions that suit {group?.label.toLowerCase() ?? "that group"}. Choose another experience, or switch back to everyone.
        </p>
        <div className="mt-6 flex flex-wrap gap-3">
          <a href={href.explore} className={primary}>Back to categories</a>
          <button type="button" onClick={() => audienceSetting.set("everyone")}
            className="inline-flex min-h-12 cursor-pointer items-center rounded-full border-2 border-plum-200 bg-surface px-6 font-bold text-plum-800 hover:bg-plum-50">
            Show everyone's questions
          </button>
        </div>
      </div>
    );
  }

  const isTrivia = categoryId === "trivia";
  return (
    <SetPlay set={set} backHref={href.explore} backLabel="Back to categories"
      beforeDepth={isTrivia ? <TopicPicker /> : group ? (
        <p className="mt-5 text-sm font-semibold text-muted">
          Questions for {group.label.toLowerCase()}. <a href={href.explore} className="font-bold text-plum-700 underline decoration-plum-300 underline-offset-4 hover:decoration-plum-600 dark:text-onplum-soft">Change</a>
        </p>
      ) : undefined} />
  );
}
