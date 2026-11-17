import { ArrowRight, Shuffle } from "lucide-react";
import { CategoryCard } from "../components/CategoryCard";
import { DailyQuestion } from "../components/DailyQuestion";
import { ContinueCard } from "../components/ContinueCard";
import { InstallButton } from "../components/InstallButton";
import { ModeCards } from "../components/ModeCards";
import { categories } from "../data/categories";
import { questions } from "../data/questions";
import { href } from "../utils/router";
import { numberWord } from "../utils/words";

const sampleCards = [
  { text: "When do you feel most loved?", tone: "bg-tint-rose border-tint-rose-line", turn: "-rotate-6", pos: "left-0 top-6" },
  { text: "Would you rather read minds or be invisible for a day?", tone: "bg-tint-lavender border-tint-lavender-line", turn: "rotate-3", pos: "left-16 top-36" },
  { text: "What's your most ridiculous hidden talent?", tone: "bg-tint-yellow border-tint-yellow-line", turn: "-rotate-2", pos: "left-2 top-64" },
];

export function Home() {
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
              Closer is a free app of {questions.length} questions and games for couples, friends, families and teams. Pick an
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
              <InstallButton className="inline-flex min-h-12 cursor-pointer items-center gap-2 rounded-full px-4 font-bold text-plum-700 transition hover:bg-sand dark:text-onplum-soft" />
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

        <section aria-labelledby="explore-heading">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div>
              <h2 id="explore-heading" className="text-2xl font-extrabold tracking-tight sm:text-4xl">Explore experiences</h2>
              <p className="mt-2 text-muted">{numberWord(categories.length)} ways to start a conversation, {questions.length} questions in all. Pick one and dive in.</p>
            </div>
          </div>
          <div className="mt-6 grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-3">
            {categories.map((category, i) => <CategoryCard key={category.id} category={category} index={i} />)}
          </div>
        </section>

        <section aria-labelledby="modes-heading">
          <h2 id="modes-heading" className="text-2xl font-extrabold tracking-tight sm:text-4xl">More ways to play</h2>
          <p className="mt-2 text-muted">Games for a group, a seasonal pack, or questions you write yourself.</p>
          <div className="mt-6">
            <ModeCards />
          </div>
        </section>
      </div>
    </>
  );
}
