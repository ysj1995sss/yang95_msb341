import { ChevronRight, Calendar, Gamepad2, PenLine, type LucideIcon } from "lucide-react";
import { orderedPacks, inSeason } from "../data/packs";
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

/** The ways to play that aren't one of the ten categories. Plain rows, so the ten colored
 *  categories above them stay the stars of the page. */
export function ModeCards() {
  const today = new Date();
  const seasonal = orderedPacks(today).find((p) => inSeason(p, today));
  const mine = useCustomQuestions().length;
  const modes: Mode[] = [
    { title: "Games", text: "Guess My Answer, Debate Night and Surprise me. Play together on one device.", to: href.games, icon: Gamepad2, gradient: "from-plum-600 to-coral-500" },
    { title: "Seasonal packs", text: "Valentine's, summer, spooky season and more.", to: href.packs, icon: Calendar, gradient: "from-amber-400 to-coral-500", badge: seasonal ? `In season: ${seasonal.name}` : undefined },
    { title: "My questions", text: "Write your own and play them any time.", to: href.mine, icon: PenLine, gradient: "from-sky-400 to-plum-600", badge: mine ? `${mine} saved` : undefined },
  ];
  return (
    <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
      {modes.map((m, i) => (
        <li key={m.title}>
          <a href={m.to} style={{ animationDelay: `${i * 40}ms` }}
            className="group flex h-full min-h-20 animate-fade-up items-center gap-4 rounded-2xl border border-plum-100 bg-surface p-4 transition duration-200 hover:border-plum-300 hover:shadow-md">
            <span aria-hidden className={`inline-flex size-11 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br ${m.gradient} text-white`}>
              <m.icon className="size-5" />
            </span>
            <span className="min-w-0 flex-1">
              <span className="flex flex-wrap items-center gap-x-2 gap-y-1">
                <h3 className="font-bold leading-snug">{m.title}</h3>
                {m.badge && <span className="rounded-full bg-coral-100 px-2.5 py-0.5 text-xs font-bold text-coral-700">{m.badge}</span>}
              </span>
              <span className="mt-0.5 block text-sm leading-snug text-muted">{m.text}</span>
            </span>
            <ChevronRight aria-hidden className="size-5 shrink-0 text-muted transition-transform group-hover:translate-x-0.5 group-hover:text-plum-600" />
          </a>
        </li>
      ))}
    </ul>
  );
}
