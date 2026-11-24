import { AUDIENCES, audienceSetting } from "../data/audience";
import { useSetting } from "../hooks";
import { href } from "../utils/router";

/** "Questions for teams · Change": says which group the questions are narrowed to (chosen on Explore),
 *  so a filter set earlier is never hidden. Shows nothing when everyone's questions are in play. */
export function AudienceNote() {
  const audience = useSetting(audienceSetting);
  const group = AUDIENCES.find((a) => a.id === audience);
  if (!group) return null;
  return (
    <p className="mt-5 text-sm font-semibold text-muted">
      Questions for {group.label.toLowerCase()} <span aria-hidden>·</span>{" "}
      <a href={href.explore} className="font-bold text-plum-700 underline decoration-plum-300 underline-offset-4 hover:decoration-plum-600 dark:text-onplum-soft">Change</a>
    </p>
  );
}
