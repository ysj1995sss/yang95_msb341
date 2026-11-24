import type { ReactNode } from "react";
import { neutralTone } from "./tint";

/** The big card a question sits on: the star of the play screen. `key` it by question so each new
 *  question animates in. `tone` is the category's pastel (see tint.ts); without one it is plain. */
export function QuestionCard({ eyebrow, text, action, tone = neutralTone, children }: {
  eyebrow: ReactNode;
  text: string;
  /** Sits at the top right of the card, e.g. the favorite heart. */
  action?: ReactNode;
  tone?: string;
  children?: ReactNode;
}) {
  return (
    <article className={`animate-fade-up rounded-[2rem] border p-6 shadow-lg max-[399px]:p-5 sm:p-10 ${tone}`}>
      <div className="flex items-start justify-between gap-3">
        <p className="flex flex-wrap items-center gap-x-3 gap-y-1 pt-3 text-sm font-bold uppercase tracking-wider text-coral-700">{eyebrow}</p>
        {action}
      </div>
      <h2 className="mt-4 text-3xl font-extrabold leading-tight tracking-tight text-ink max-[399px]:mt-3 max-[399px]:text-2xl sm:mt-6 sm:text-4xl">{text}</h2>
      {children}
    </article>
  );
}
