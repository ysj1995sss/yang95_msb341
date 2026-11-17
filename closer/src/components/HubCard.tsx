import { ArrowRight, type LucideIcon } from "lucide-react";
import type { CategoryTint } from "../types";
import { tintClass } from "./tint";

export interface HubEntry {
  title: string;
  /** The short bold line under the title: who it's for, or how many there are. */
  detail: string;
  text: string;
  to: string;
  cta: string;
  icon: LucideIcon;
  gradient: string;
  tint: CategoryTint;
}

/** One big tinted card on a hub page (Games, Library): the whole card is a link. */
export function HubCard({ entry, index }: { entry: HubEntry; index: number }) {
  return (
    <a href={entry.to} style={{ animationDelay: `${index * 50}ms` }}
      className={`group flex h-full animate-fade-up flex-col gap-4 rounded-3xl border p-6 shadow-sm transition duration-200 hover:-translate-y-1 hover:shadow-lg focus-visible:-translate-y-1 ${tintClass[entry.tint]}`}>
      <span aria-hidden className={`inline-flex size-14 items-center justify-center rounded-2xl bg-gradient-to-br ${entry.gradient} text-white shadow-md`}>
        <entry.icon className="size-7" />
      </span>
      <div>
        <h2 className="text-xl font-extrabold leading-snug">{entry.title}</h2>
        <p className="mt-1 text-sm font-bold text-plum-700 dark:text-onplum-soft">{entry.detail}</p>
        <p className="mt-3 leading-relaxed text-muted">{entry.text}</p>
      </div>
      <span className="mt-auto inline-flex items-center gap-1.5 font-bold text-plum-700 dark:text-onplum-soft">
        {entry.cta} <ArrowRight aria-hidden className="size-4 transition-transform group-hover:translate-x-1" />
      </span>
    </a>
  );
}

/** The grid of hub cards under a hub page's heading. */
export function HubGrid({ entries }: { entries: HubEntry[] }) {
  return (
    <ul className="mt-8 grid gap-4 sm:gap-5 md:grid-cols-3">
      {entries.map((entry, i) => <li key={entry.title}><HubCard entry={entry} index={i} /></li>)}
    </ul>
  );
}
