import type { ReactNode } from "react";

/** The big card a question sits on. `key` it by question so each new question animates in. */
export function QuestionCard({ eyebrow, text, action, children }: {
  eyebrow: ReactNode;
  text: string;
  /** Sits at the top right of the card, e.g. the favorite heart. */
  action?: ReactNode;
  children?: ReactNode;
}) {
  return (
    <article className="animate-fade-up rounded-[2rem] border border-plum-100 bg-surface p-6 shadow-lg sm:p-10">
      <div className="flex items-start justify-between gap-3">
        <p className="flex flex-wrap items-center gap-x-3 gap-y-1 pt-3 text-sm font-bold uppercase tracking-wider text-coral-700">{eyebrow}</p>
        {action}
      </div>
      <h2 className="mt-2 text-2xl font-extrabold leading-snug text-ink sm:text-3xl">{text}</h2>
      {children}
    </article>
  );
}
