import { Shuffle } from "lucide-react";
import { useMemo } from "react";
import { audienceSetting } from "../data/audience";
import { surpriseSet } from "../data/playSets";
import { useSetting } from "../hooks";
import { href } from "../utils/router";
import { SetPlay } from "./SetPlay";

/** Surprise me: one shuffled round through all the questions, no category to pick. */
export function Surprise() {
  const audience = useSetting(audienceSetting);
  const set = useMemo(() => surpriseSet(audience), [audience]);
  return (
    <SetPlay set={set} backHref={href.explore} backLabel="Back to categories"
      icon={
        <span aria-hidden className="inline-flex size-16 shrink-0 items-center justify-center rounded-3xl bg-gradient-to-br from-coral-500 to-plum-500 text-white shadow-md">
          <Shuffle className="size-8" />
        </span>
      } />
  );
}
