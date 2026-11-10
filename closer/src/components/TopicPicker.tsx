import { Brain } from "lucide-react";
import { useId } from "react";
import { questions } from "../data/questions";
import { inTopicGroup, topicGroups } from "../data/triviaTopics";
import { createSetting } from "../utils/settings";
import { isTopicGroupId } from "../data/triviaTopics";
import { useSetting } from "../hooks";

/** The trivia topic someone last chose, remembered between visits. */
export const topicSetting = createSetting<string>("closer.trivia.topic", "all", isTopicGroupId);

/** Quiz topic chips: all topics, or one group such as Geography or Science. */
export function TopicPicker() {
  const choice = useSetting(topicSetting);
  const name = useId();
  const trivia = questions.filter((q) => q.kind === "trivia");
  const options = [
    { id: "all", label: "All topics", count: trivia.length },
    ...topicGroups.map((g) => ({ id: g.id, label: g.label, count: trivia.filter((q) => inTopicGroup(q, g.id)).length })),
  ];
  return (
    <fieldset className="mt-8">
      <legend className="flex items-center gap-2 text-sm font-bold text-muted">
        <Brain aria-hidden className="size-4" /> Choose a topic
      </legend>
      <div className="mt-2 flex flex-wrap gap-2">
        {options.map((o) => (
          <label key={o.id}
            className={`inline-flex min-h-11 cursor-pointer items-center gap-2 rounded-full border-2 px-4 text-[15px] font-bold transition has-[:focus-visible]:outline-3 has-[:focus-visible]:outline-plum-500 ${
              choice === o.id ? "border-plum-600 bg-plum-600 text-white" : "border-plum-100 bg-surface text-plum-800 hover:border-plum-300"}`}>
            <input type="radio" name={name} value={o.id} checked={choice === o.id} onChange={() => topicSetting.set(o.id)} className="sr-only" />
            {o.label}
            <span className={`text-xs font-semibold ${choice === o.id ? "text-onplum" : "text-muted"}`}>{o.count}</span>
          </label>
        ))}
      </div>
    </fieldset>
  );
}
