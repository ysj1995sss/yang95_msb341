import { useId } from "react";
import { levelsFor } from "../data/depth";
import type { CategoryId, Depth } from "../types";
import type { Level } from "../utils/session";

const ORDER: Level[] = ["mix", 1, 2, 3, 4];

/** Four dots that fill up with depth: a quick visual for how deep a question goes. */
export function DepthMeter({ depth }: { depth: Depth }) {
  return (
    <span aria-hidden className="inline-flex items-center gap-1">
      {[1, 2, 3, 4].map((n) => (
        <span key={n} className={`size-2 rounded-full ${n <= depth ? "bg-coral-500" : "bg-plum-200"}`} />
      ))}
    </span>
  );
}

/** Picks how deep the questions go. Sits above the question card and can change at any time. */
export function DepthSelector({ categoryId, level, remaining, onChange }: {
  categoryId: CategoryId;
  level: Level;
  /** Unseen questions per level, shown as "n left". */
  remaining: Record<Depth, number>;
  onChange: (level: Level) => void;
}) {
  const levels = levelsFor(categoryId);
  const group = useId();
  const quiz = categoryId === "trivia";
  const active = level === "mix" ? null : levels[level];
  return (
    <section aria-label={quiz ? "Difficulty" : "Question depth"}>
      <div role="radiogroup" aria-label={quiz ? "Difficulty" : "Question depth"} className="grid grid-cols-5 gap-1.5 sm:gap-2">
        {ORDER.map((option) => {
          const checked = option === level;
          const left = option === "mix" ? null : remaining[option];
          const name = option === "mix" ? "Mix" : levels[option].name;
          return (
            <label
              key={option}
              className={`flex min-h-14 cursor-pointer flex-col items-center justify-center gap-1 rounded-2xl border-2 px-1 py-1.5 text-center text-[13px] font-bold leading-tight transition has-[:focus-visible]:outline-3 has-[:focus-visible]:outline-plum-500 sm:text-sm ${
                checked ? "border-plum-600 bg-plum-600 text-white shadow-md" : "border-plum-100 bg-white text-plum-800 hover:border-plum-300"
              }`}
            >
              <input type="radio" name={group} value={String(option)} checked={checked} onChange={() => onChange(option)} className="sr-only" />
              {option === "mix" ? (
                <span aria-hidden className="text-xs">All levels</span>
              ) : (
                <span aria-hidden className="inline-flex items-center gap-1">
                  {[1, 2, 3, 4].map((n) => (
                    <span key={n} className={`size-1.5 rounded-full ${n <= option ? (checked ? "bg-white" : "bg-coral-500") : checked ? "bg-white/40" : "bg-plum-200"}`} />
                  ))}
                </span>
              )}
              <span>{name}</span>
              {left !== null && <span className={`text-[11px] font-semibold ${checked ? "text-plum-100" : "text-muted"}`}>{left} left</span>}
            </label>
          );
        })}
      </div>
      <p role="status" className="mt-2 text-center text-sm text-muted">
        {active ? (
          <><span className="font-bold text-plum-800">{active.name}:</span> {active.hint}</>
        ) : (
          <><span className="font-bold text-plum-800">Mix:</span> questions from every level, in a random order</>
        )}
      </p>
    </section>
  );
}
