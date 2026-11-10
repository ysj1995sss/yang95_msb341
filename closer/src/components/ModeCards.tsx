import { ArrowRight, Calendar, Mic, PenLine, Shuffle, Users, type LucideIcon } from "lucide-react";
import { orderedPacks, inSeason } from "../data/packs";
import { questions } from "../data/questions";
import { useCustomQuestions } from "../hooks";
import { href } from "../utils/router";

interface Mode {
  title: string;
  text: string;
  to: string;
  icon: LucideIcon;
  gradient: string;
  badge?: string;
}

/** The ways to play that aren't one of the ten categories. */
export function ModeCards() {
  const today = new Date();
  const seasonal = orderedPacks(today).find((p) => inSeason(p, today));
  const mine = useCustomQuestions().length;
  const modes: Mode[] = [
    { title: "Surprise me", text: `One tap, any of the ${questions.length} questions.`, to: href.surprise, icon: Shuffle, gradient: "from-coral-500 to-plum-500" },
    { title: "Guess My Answer", text: "2 to 6 players, one device. Pick a secret answer, then see who can guess it.", to: href.guess, icon: Users, gradient: "from-plum-600 to-coral-500" },
    { title: "Debate Night", text: "Two sides, a timer, and the room votes on who argued better.", to: href.debate, icon: Mic, gradient: "from-plum-500 to-sky-400" },
    { title: "Seasonal packs", text: "Valentine's, summer, spooky season and more.", to: href.packs, icon: Calendar, gradient: "from-amber-400 to-coral-500", badge: seasonal ? `In season: ${seasonal.name}` : undefined },
    { title: "My questions", text: "Write your own and play them any time.", to: href.mine, icon: PenLine, gradient: "from-sky-400 to-plum-600", badge: mine ? `${mine} saved` : undefined },
  ];
  return (
    <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {modes.map((m, i) => (
        <li key={m.title}>
          <a href={m.to} style={{ animationDelay: `${i * 40}ms` }}
            className="group flex h-full animate-fade-up flex-col gap-3 rounded-3xl border border-plum-100 bg-surface/80 p-5 shadow-sm transition duration-200 hover:-translate-y-1 hover:border-plum-200 hover:shadow-lg focus-visible:-translate-y-1">
            <div className="flex items-start justify-between gap-3">
              <span aria-hidden className={`inline-flex size-12 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br ${m.gradient} text-white shadow-md`}>
                <m.icon className="size-6" />
              </span>
              {m.badge && <span className="rounded-full bg-coral-100 px-3 py-1 text-xs font-bold text-coral-700">{m.badge}</span>}
            </div>
            <div>
              <h3 className="text-lg font-bold leading-snug">{m.title}</h3>
              <p className="mt-1 text-[15px] leading-relaxed text-muted">{m.text}</p>
            </div>
            <span className="mt-auto inline-flex items-center gap-1.5 text-[15px] font-bold text-plum-700 dark:text-onplum-soft">
              Open <ArrowRight aria-hidden className="size-4 transition-transform group-hover:translate-x-1" />
            </span>
          </a>
        </li>
      ))}
    </ul>
  );
}
