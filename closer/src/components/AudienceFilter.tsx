import { Users } from "lucide-react";
import { useId } from "react";
import { AUDIENCES, audienceCounts, audienceSetting } from "../data/audience";
import { questions } from "../data/questions";
import { useSetting } from "../hooks";
import type { AudienceChoice } from "../types";

/** "Who's playing?": narrows every category to the questions that suit couples, friends, family or a team. */
export function AudienceFilter() {
  const choice = useSetting(audienceSetting);
  const name = useId();
  const options: { id: AudienceChoice; label: string; count: number; blurb: string }[] = [
    { id: "everyone", label: "Everyone", count: questions.length, blurb: "All the questions" },
    ...AUDIENCES.map((a) => ({ id: a.id as AudienceChoice, label: a.label, count: audienceCounts[a.id], blurb: a.blurb })),
  ];
  return (
    <fieldset className="mt-8">
      <legend className="flex items-center gap-2 text-sm font-bold text-muted">
        <Users aria-hidden className="size-4" /> Who's playing?
      </legend>
      <div className="mt-2 flex flex-wrap gap-2">
        {options.map((o) => (
          <label key={o.id} title={o.blurb}
            className={`inline-flex min-h-11 cursor-pointer items-center gap-2 rounded-full border-2 px-4 text-[15px] font-bold transition has-[:focus-visible]:outline-3 has-[:focus-visible]:outline-plum-500 ${
              choice === o.id ? "border-plum-600 bg-plum-600 text-white" : "border-plum-100 bg-surface text-plum-800 hover:border-plum-300"}`}>
            <input type="radio" name={name} value={o.id} checked={choice === o.id} onChange={() => audienceSetting.set(o.id)} className="sr-only" />
            {o.label}
            <span className={`text-xs font-semibold ${choice === o.id ? "text-onplum" : "text-muted"}`}>{o.count}</span>
          </label>
        ))}
      </div>
    </fieldset>
  );
}
