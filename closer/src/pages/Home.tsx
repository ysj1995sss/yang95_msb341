import { ArrowRight, Shuffle } from "lucide-react";
import { CategoryCard } from "../components/CategoryCard";
import { DailyQuestion } from "../components/DailyQuestion";
import { ContinueCard } from "../components/ContinueCard";
import { HowItWorks } from "../components/HowItWorks";
import { InstallButton } from "../components/InstallButton";
import { ModeCards } from "../components/ModeCards";
import { categories } from "../data/categories";
import { questions } from "../data/questions";
import { href } from "../utils/router";

const sampleCards = [
  { text: "When do you feel most loved?", tone: "bg-surface text-ink", turn: "-rotate-6", pos: "left-0 top-8" },
  { text: "Would you rather read minds or be invisible for a day?", tone: "bg-plum-600 text-cream", turn: "rotate-3", pos: "left-14 top-36" },
  { text: "What's your most ridiculous hidden talent?", tone: "bg-coral-400 text-plum-900", turn: "-rotate-2", pos: "left-4 top-64" },
];

export function Home() {
  return (
    <>
      <section className="relative overflow-hidden">
        <div aria-hidden className="pointer-events-none absolute -left-24 top-10 size-72 rounded-full bg-plum-200/60 blur-3xl" />
        <div aria-hidden className="pointer-events-none absolute -right-24 top-40 size-72 rounded-full bg-coral-200/60 blur-3xl" />
        <div className="relative mx-auto grid max-w-6xl items-center gap-12 px-4 pb-16 pt-12 sm:px-6 sm:pt-20 lg:grid-cols-[1.1fr_0.9fr]">
          <div className="animate-fade-up">
            <p className="inline-flex rounded-full bg-coral-100 px-4 py-1.5 text-sm font-bold text-coral-700">Every connection starts with a question.</p>
            <h1 tabIndex={-1} className="mt-5 text-4xl font-extrabold leading-[1.08] tracking-tight sm:text-6xl">
              Better questions. <span className="bg-gradient-to-r from-plum-600 to-coral-500 bg-clip-text text-transparent">Stronger connections.</span>
            </h1>
            <p className="mt-5 max-w-xl text-xl font-semibold leading-snug text-ink">
              Closer is a free app of {questions.length} questions and games for couples, friends, families and teams. Pick an
              experience, read a question out loud, and start talking.
            </p>
            <p className="mt-3 max-w-xl text-lg leading-relaxed text-muted">
              Turn ordinary moments into unforgettable conversations. Explore questions for every relationship, mood, and occasion.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <a href={href.explore} className="inline-flex min-h-12 items-center gap-2 rounded-full bg-plum-600 px-7 font-bold text-white shadow-lg shadow-plum-600/25 transition hover:bg-plum-700">
                Start Exploring <ArrowRight aria-hidden className="size-5" />
              </a>
              <a href={href.surprise}
                className="inline-flex min-h-12 items-center gap-2 rounded-full border-2 border-plum-200 bg-surface/70 px-7 font-bold text-plum-800 transition hover:border-plum-300 hover:bg-surface">
                <Shuffle aria-hidden className="size-5" /> Surprise me
              </a>
            </div>
            <div className="mt-4 flex flex-wrap items-start gap-3">
              <button type="button" onClick={() => document.getElementById("how-it-works")?.scrollIntoView()}
                className="inline-flex min-h-12 cursor-pointer items-center rounded-full px-5 font-bold text-muted transition hover:bg-sand hover:text-ink">
                How It Works
              </button>
              <InstallButton className="inline-flex min-h-12 cursor-pointer items-center gap-2 rounded-full px-5 font-bold text-plum-700 transition hover:bg-sand dark:text-onplum-soft" />
            </div>
          </div>
          <div aria-hidden className="relative mx-auto hidden h-96 w-full max-w-sm sm:block">
            {sampleCards.map((card, i) => (
              <div key={card.text} style={{ animationDelay: `${i * 0.8}s` }}
                className={`absolute w-72 animate-float rounded-3xl p-6 text-lg font-bold leading-snug shadow-xl ${card.tone} ${card.turn} ${card.pos}`}>
                {card.text}
              </div>
            ))}
          </div>
        </div>
      </section>

      <div className="mx-auto max-w-6xl space-y-20 px-4 sm:px-6">
        <ContinueCard />

        <DailyQuestion />

        <section aria-labelledby="explore-heading">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div>
              <h2 id="explore-heading" className="text-3xl font-extrabold tracking-tight sm:text-4xl">Explore experiences</h2>
              <p className="mt-2 text-muted">Ten ways to start a conversation, {questions.length} questions in all. Pick one and dive in.</p>
            </div>
          </div>
          <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {categories.map((category, i) => <CategoryCard key={category.id} category={category} index={i} />)}
          </div>
        </section>

        <section aria-labelledby="modes-heading">
          <h2 id="modes-heading" className="text-3xl font-extrabold tracking-tight sm:text-4xl">More ways to play</h2>
          <p className="mt-2 text-muted">Games for a group, a seasonal pack, or questions you write yourself.</p>
          <div className="mt-8">
            <ModeCards />
          </div>
        </section>

        <HowItWorks id="how-it-works" />
      </div>
    </>
  );
}
