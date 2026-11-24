import { useMemo } from "react";
import { AudienceNote } from "../components/AudienceNote";
import { primary } from "../components/ui";
import { AUDIENCES, audienceSetting } from "../data/audience";
import { categoryById } from "../data/categories";
import { categorySet } from "../data/playSets";
import { useSetting } from "../hooks";
import { href } from "../utils/router";
import { ChoicesExperience } from "./ChoicesExperience";
import { SetPlay } from "./SetPlay";
import { TriviaExperience } from "./TriviaExperience";

export function QuestionExperience({ categoryId }: { categoryId: string }) {
  return categoryId === "trivia" ? <TriviaExperience /> : categoryById(categoryId)?.id === "would-you-rather" ? <ChoicesExperience /> : <Conversation categoryId={categoryId} />;
}

function Conversation({ categoryId }: { categoryId: string }) {
  const audience = useSetting(audienceSetting);
  const set = useMemo(() => categorySet(categoryId, audience), [categoryId, audience]);

  if (!set) {
    return (
      <div className="mx-auto max-w-3xl px-4 pt-16 sm:px-6">
        <h1 tabIndex={-1} className="text-3xl font-extrabold">We couldn't find that experience</h1>
        <p className="mt-3 text-muted">It may have moved. Pick one of the experiences instead.</p>
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

  return (
    <SetPlay set={set} backHref={href.explore} backLabel="Back to categories"
      beforeDepth={<AudienceNote />} />
  );
}
