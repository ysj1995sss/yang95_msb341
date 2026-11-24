import { audienceSetting } from "../data/audience";
import { categories } from "../data/categories";
import { categorySet } from "../data/playSets";
import { useSetting } from "../hooks";
import { gridSpans } from "../utils/gridSpans";
import { CategoryCard } from "./CategoryCard";
import { topicSetting } from "../utils/triviaTopicSetting";

// Written out in full so Tailwind sees every class.
const baseSpan = { 1: "col-span-1", 2: "col-span-2" } as const;
const wideSpan = { 1: "lg:col-span-1", 2: "lg:col-span-2", 3: "lg:col-span-3" } as const;

/** The experience cards. The audience filter can hide some, so the cards that are left are sized to
 *  fill every row: on a phone the odd one out takes a full row, on a wide screen the first and last
 *  cards stretch when the count needs it. */
export function CategoryGrid() {
  const audience = useSetting(audienceSetting);
  const topic = useSetting(topicSetting);
  const visible = categories.filter((category) => (categorySet(category.id, audience, topic)?.pool.length ?? 0) > 0);
  const spans = gridSpans(visible.length);
  return (
    <div className="grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-3" aria-live="polite" data-audience={audience}>
      {visible.map((category, i) => (
        <CategoryCard key={category.id} category={category} index={i} className={`${baseSpan[spans[i]!.base]} ${wideSpan[spans[i]!.wide]}`} />
      ))}
    </div>
  );
}
