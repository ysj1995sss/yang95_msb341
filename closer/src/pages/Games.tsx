import { ArrowRight, Mic, Shuffle, Users, type LucideIcon } from "lucide-react";
import { tintClass } from "../components/tint";
import { questions } from "../data/questions";
import type { CategoryTint } from "../types";
import { href } from "../utils/router";

interface Game {
  title: string;
  who: string;
  text: string;
  to: string;
  cta: string;
  icon: LucideIcon;
  gradient: string;
  tint: CategoryTint;
}

const games: Game[] = [
  {
    title: "Guess My Answer", who: "2 to 6 players", to: href.guess, cta: "Play", icon: Users, tint: "lavender", gradient: "from-plum-600 to-coral-500",
    text: "One person secretly picks an answer, the device is passed around, and everyone else guesses. Right guesses score.",
  },
  {
    title: "Debate Night", who: "2 players and a room", to: href.debate, cta: "Play", icon: Mic, tint: "peach", gradient: "from-plum-500 to-sky-400",
    text: "Two sides, a speaking clock for each, and the room votes on who argued better.",
  },
  {
    title: "Surprise me", who: "1 or more", to: href.surprise, cta: "Shuffle", icon: Shuffle, tint: "rose", gradient: "from-coral-500 to-plum-500",
    text: `One shuffled round through all ${questions.length} questions. No category to pick.`,
  },
];

/** The ways to play together: one page for the games, instead of three links in the menu. */
export function Games() {
  return (
    <div className="mx-auto max-w-5xl px-4 pt-10 sm:px-6 sm:pt-14">
      <h1 tabIndex={-1} className="text-4xl font-extrabold tracking-tight sm:text-5xl">Games</h1>
      <p className="mt-3 max-w-2xl text-lg text-muted">Play together on one phone or one screen. Nothing to sign up for, nothing to type.</p>
      <ul className="mt-8 grid gap-4 sm:gap-5 md:grid-cols-3">
        {games.map((g, i) => (
          <li key={g.title}>
            <a href={g.to} style={{ animationDelay: `${i * 50}ms` }}
              className={`group flex h-full animate-fade-up flex-col gap-4 rounded-3xl border p-6 shadow-sm transition duration-200 hover:-translate-y-1 hover:shadow-lg focus-visible:-translate-y-1 ${tintClass[g.tint]}`}>
              <span aria-hidden className={`inline-flex size-14 items-center justify-center rounded-2xl bg-gradient-to-br ${g.gradient} text-white shadow-md`}>
                <g.icon className="size-7" />
              </span>
              <div>
                <h2 className="text-xl font-extrabold leading-snug">{g.title}</h2>
                <p className="mt-1 text-sm font-bold text-plum-700 dark:text-onplum-soft">{g.who}</p>
                <p className="mt-3 leading-relaxed text-muted">{g.text}</p>
              </div>
              <span className="mt-auto inline-flex items-center gap-1.5 font-bold text-plum-700 dark:text-onplum-soft">
                {g.cta} <ArrowRight aria-hidden className="size-4 transition-transform group-hover:translate-x-1" />
              </span>
            </a>
          </li>
        ))}
      </ul>
    </div>
  );
}
