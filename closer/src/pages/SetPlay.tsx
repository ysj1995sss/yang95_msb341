import type { ReactNode } from "react";
import { SessionView } from "../components/SessionView";
import type { PlaySet } from "../data/playSets";

/** Plays a play set (a category, the surprise mix, a pack or your own questions) with its saved progress.
 *  Keyed by the set, so changing the group or topic starts that set's own round. */
export function SetPlay({ set, backHref, backLabel, icon, beforeDepth }: {
  set: PlaySet;
  backHref: string;
  backLabel: string;
  icon?: ReactNode;
  beforeDepth?: ReactNode;
}) {
  return (
    <SessionView key={set.key} category={set.category} heading={set.title} description={set.description} pool={set.pool}
      limit={set.limit} persistKey={set.key} timer={set.timer} backHref={backHref} backLabel={backLabel}
      icon={icon} beforeDepth={beforeDepth} />
  );
}
