import { ArrowRight, Users } from "lucide-react";
import { href } from "../utils/router";

/** Points to the two-player game, which isn't one of the ten categories. */
export function GuessPromo() {
  return (
    <a href={href.guess}
      className="group flex flex-col gap-4 rounded-[2rem] bg-gradient-to-br from-plum-700 to-plum-600 p-6 text-cream shadow-lg transition hover:shadow-xl sm:flex-row sm:items-center sm:p-8">
      <span aria-hidden className="inline-flex size-14 shrink-0 items-center justify-center rounded-2xl bg-white/15">
        <Users className="size-7" />
      </span>
      <span className="flex-1">
        <span className="block text-xl font-extrabold">Guess My Answer</span>
        <span className="mt-1 block text-plum-100">
          A two-player game on one device. Pick a secret answer, then see if your partner can guess it.
        </span>
      </span>
      <span className="inline-flex items-center gap-1.5 font-bold">
        Play now <ArrowRight aria-hidden className="size-5 transition-transform group-hover:translate-x-1" />
      </span>
    </a>
  );
}
