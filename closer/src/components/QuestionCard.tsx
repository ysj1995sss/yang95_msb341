import type { ReactNode } from "react";

/** The big card a question sits on. `key` it by question so each new question animates in. */
export function QuestionCard({ eyebrow, text, children }: { eyebrow: string; text: string; children?: ReactNode }) {
  return (
    <article className="animate-fade-up rounded-[2rem] border border-plum-100 bg-white p-6 shadow-lg sm:p-10">
      <p className="text-sm font-bold uppercase tracking-wider text-coral-700">{eyebrow}</p>
      <h2 className="mt-3 text-2xl font-extrabold leading-snug text-ink sm:text-3xl">{text}</h2>
      {children}
    </article>
  );
}
