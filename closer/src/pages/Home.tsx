import { ArrowRight, Shuffle } from "lucide-react";
import { DailyQuestion } from "../components/DailyQuestion";
import { ContinueCard } from "../components/ContinueCard";
import { InstallButton } from "../components/InstallButton";
import { useInstallCardShown } from "../hooks";
import { questions } from "../data/questions";
import { href } from "../utils/router";

const sampleCards = [
  { text: "When do you feel most loved?", tone: "bg-tint-rose border-tint-rose-line", turn: "-rotate-6", pos: "left-0 top-6" },
  { text: "Would you rather read minds or be invisible for a day?", tone: "bg-tint-lavender border-tint-lavender-line", turn: "rotate-3", pos: "left-16 top-36" },
  { text: "What's your most ridiculous hidden talent?", tone: "bg-tint-yellow border-tint-yellow-line", turn: "-rotate-2", pos: "left-2 top-64" },
];

export function Home() {
  // On a phone the "Install Closer" card above the page already offers this (the card is phone-only).
  const installCard = useInstallCardShown();
  return (
    <>
      <section className="relative overflow-hidden">
        <div aria-hidden className="pointer-events-none absolute -left-24 top-0 size-72 rounded-full bg-plum-200/50 blur-3xl" />
        <div aria-hidden className="pointer-events-none absolute -right-24 top-32 size-72 rounded-full bg-coral-200/50 blur-3xl" />
        <div className="relative mx-auto grid max-w-6xl items-center gap-10 px-4 pb-12 pt-10 sm:px-6 sm:pt-16 lg:grid-cols-[1.1fr_0.9fr]">
          <div className="animate-fade-up">
            <h1 tabIndex={-1} className="text-4xl font-extrabold leading-[1.08] tracking-tight sm:text-6xl">
              Better questions. <span className="bg-gradient-to-r from-plum-600 to-coral-500 bg-clip-text text-transparent">Stronger connections.</span>
            </h1>
            <p className="mt-5 max-w-xl text-lg leading-relaxed text-muted sm:text-xl">
              Closer is a free app of {questions.length.toLocaleString("en-US")} questions and games for couples, friends, families and teams. Pick an
              experience, read a question out loud, and start talking.
            </p>
            <div className="mt-7 flex flex-wrap items-center gap-3">
              <a href={href.explore} className="inline-flex min-h-12 items-center gap-2 rounded-full bg-plum-600 px-7 font-bold text-white shadow-lg shadow-plum-600/25 transition hover:bg-plum-700">
                Start Exploring <ArrowRight aria-hidden className="size-5" />
              </a>
              <a href={href.surprise}
                className="inline-flex min-h-12 items-center gap-2 rounded-full border-2 border-plum-200 bg-surface/70 px-7 font-bold text-plum-800 transition hover:border-plum-300 hover:bg-surface">
                <Shuffle aria-hidden className="size-5" /> Surprise me
              </a>
              <InstallButton className={`inline-flex min-h-12 cursor-pointer items-center gap-2 rounded-full px-4 font-bold text-plum-700 transition hover:bg-sand dark:text-onplum-soft ${installCard ? "max-sm:hidden" : ""}`} />
            </div>
          </div>
          <div aria-hidden className="relative mx-auto hidden h-96 w-full max-w-sm sm:block">
            {sampleCards.map((card, i) => (
              <div key={card.text} style={{ animationDelay: `${i * 0.8}s` }}
                className={`absolute w-72 animate-float rounded-3xl border p-6 text-lg font-bold leading-snug text-ink shadow-lg ${card.tone} ${card.turn} ${card.pos}`}>
                {card.text}
              </div>
            ))}
          </div>
        </div>
      </section>

      <div className="mx-auto max-w-6xl space-y-14 px-4 sm:space-y-16 sm:px-6">
        <ContinueCard />

        <DailyQuestion />
      </div>
    </>
  );
}
