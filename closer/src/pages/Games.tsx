import { Mic, Shuffle, SlidersHorizontal, Users, X } from "lucide-react";
import { useEffect, useId, useState } from "react";
import { HubGrid, type HubEntry } from "../components/HubCard";
import { gameGroups, games, moodLabels, type GameMood } from "../data/games";
import {
  fitsFilter, isFiltered, loadGameFilter, NO_FILTER, playerChoices, saveGameFilter,
  type Filterable, type GameFilter, type MoodChoice, type PlayerChoice,
} from "../utils/gameFilter";
import { href } from "../utils/router";
import { sessionStore } from "../utils/visit";

type Entry = HubEntry & Filterable;

const questionGames: Entry[] = [
  {
    title: "Guess My Answer", detail: "2 to 6 players", to: href.guess, cta: "Play", icon: Users, tint: "lavender", gradient: "from-plum-600 to-coral-500",
    text: "One person secretly picks an answer, the device is passed around, and everyone else guesses. Right guesses score.",
    min: 2, max: 6, moods: ["know", "competitive"],
  },
  {
    title: "Debate Night", detail: "2 players and a room", to: href.debate, cta: "Play", icon: Mic, tint: "peach", gradient: "from-plum-500 to-sky-400",
    text: "Two sides, a speaking clock for each, and the room votes on who argued better.",
    min: 2, max: 20, moods: ["competitive"],
  },
  {
    title: "Surprise me", detail: "1 or more", to: href.surprise, cta: "Shuffle", icon: Shuffle, tint: "rose", gradient: "from-coral-500 to-plum-500",
    text: "One shuffled round through the whole question library, or the part of it that suits your group. No experience to pick.",
    min: 1, max: 20, moods: ["quick", "know"],
  },
];

const sections: { id: string; title: string; text: string; entries: Entry[] }[] = [
  ...gameGroups.map((group) => ({
    id: group.id, title: group.title, text: group.text,
    entries: games.filter((g) => g.group === group.id).map<Entry>((g) => ({
      title: g.title, detail: g.players, text: g.text, to: href.game(g.id), cta: "Play", icon: g.icon, gradient: g.gradient, tint: g.tint,
      min: g.min, max: g.max, moods: g.moods,
    })),
  })),
  { id: "questions", title: "Question games", text: "Built on the question library.", entries: questionGames },
];

const total = sections.reduce((n, s) => n + s.entries.length, 0);

const moodChoices: { id: MoodChoice; label: string }[] = [
  { id: "any", label: "Anything" },
  ...(Object.keys(moodLabels) as GameMood[]).map((id) => ({ id, label: moodLabels[id] })),
];

const chip = (on: boolean) =>
  `inline-flex min-h-11 cursor-pointer items-center rounded-full border-2 px-4 text-[15px] font-bold transition has-[:focus-visible]:outline-3 has-[:focus-visible]:outline-plum-500 ${
    on ? "border-plum-600 bg-plum-600 text-white" : "border-plum-100 bg-surface text-plum-800 hover:border-plum-300"}`;

/** One row of single-choice chips. */
function ChipRow<T extends string>({ legend, choices, value, onChange }: {
  legend: string; choices: readonly { id: T; label: string }[]; value: T; onChange: (id: T) => void;
}) {
  const name = useId();
  return (
    <fieldset>
      <legend className="text-sm font-bold text-muted">{legend}</legend>
      <div className="mt-2 flex flex-wrap gap-2">
        {choices.map((c) => (
          <label key={c.id} className={chip(value === c.id)}>
            <input type="radio" name={name} value={c.id} checked={value === c.id} onChange={() => onChange(c.id)} className="sr-only" />
            {c.label}
          </label>
        ))}
      </div>
    </fieldset>
  );
}

/** Scrolls to a group of games and moves focus to its heading. */
function jumpTo(id: string) {
  const heading = document.getElementById(`games-${id}`);
  if (!heading) return;
  heading.scrollIntoView({ block: "start" });
  heading.focus({ preventScroll: true });
}

/** The ways to play together: every game, in groups, with a quick filter and links to each group. */
export function Games() {
  const [filter, setFilter] = useState<GameFilter>(() => loadGameFilter(sessionStore()));
  useEffect(() => saveGameFilter(filter, sessionStore()), [filter]);

  const shown = sections
    .map((s) => ({ ...s, entries: s.entries.filter((e) => fitsFilter(e, filter)) }))
    .filter((s) => s.entries.length > 0);
  const count = shown.reduce((n, s) => n + s.entries.length, 0);
  const filtered = isFiltered(filter);

  return (
    <div className="mx-auto max-w-5xl px-4 pb-4 pt-10 sm:px-6 sm:pt-14">
      <h1 tabIndex={-1} className="text-4xl font-extrabold tracking-tight sm:text-5xl">Games</h1>
      <p className="mt-3 max-w-2xl text-lg text-muted">
        {total} games to play together on one phone or one screen. Nothing to sign up for, and names are never saved.
      </p>

      <section aria-labelledby="games-filter" className="mt-8 rounded-3xl bg-surface/80 p-4 ring-1 ring-plum-100 sm:p-5">
        <h2 id="games-filter" className="flex items-center gap-2 text-lg font-extrabold">
          <SlidersHorizontal aria-hidden className="size-5 text-plum-600 dark:text-onplum-soft" /> Find a game
        </h2>
        <div className="mt-3 space-y-4">
          <ChipRow<PlayerChoice> legend="How many of you?" choices={playerChoices} value={filter.players}
            onChange={(players) => setFilter((f) => ({ ...f, players }))} />
          <ChipRow<MoodChoice> legend="In the mood for" choices={moodChoices} value={filter.mood}
            onChange={(mood) => setFilter((f) => ({ ...f, mood }))} />
        </div>
        <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
          <p role="status" className="text-[15px] font-semibold text-muted">
            {filtered ? `${count} of ${total} games fit` : `All ${total} games`}
          </p>
          {filtered && (
            <button type="button" onClick={() => setFilter(NO_FILTER)}
              className="inline-flex min-h-11 cursor-pointer items-center gap-1.5 rounded-full px-3 text-[15px] font-bold text-plum-700 hover:bg-plum-50 dark:text-onplum-soft">
              <X aria-hidden className="size-4" /> Clear filters
            </button>
          )}
        </div>
      </section>

      {shown.length > 1 && (
        <nav aria-label="Game groups" className="mt-6">
          <ul className="flex flex-wrap gap-2">
            {shown.map((s) => (
              <li key={s.id}>
                <button type="button" onClick={() => jumpTo(s.id)}
                  className="inline-flex min-h-11 cursor-pointer items-center rounded-full bg-plum-50 px-4 text-sm font-bold text-plum-800 transition hover:bg-plum-100 dark:bg-plum-900/40 dark:text-onplum-soft">
                  {s.title}
                </button>
              </li>
            ))}
          </ul>
        </nav>
      )}

      {shown.length === 0 && (
        <div className="mt-10 rounded-3xl bg-surface/80 p-6 text-center ring-1 ring-plum-100">
          <p className="text-lg font-bold">No game fits both choices.</p>
          <p className="mt-1 text-muted">Try a different mood, or another number of players.</p>
          <button type="button" onClick={() => setFilter(NO_FILTER)}
            className="mt-4 inline-flex min-h-12 cursor-pointer items-center rounded-full bg-plum-600 px-6 font-bold text-white hover:bg-plum-700">
            Show every game
          </button>
        </div>
      )}

      {shown.map((section) => (
        <section key={section.id} aria-labelledby={`games-${section.id}`} className="mt-10">
          <h2 id={`games-${section.id}`} tabIndex={-1} className="scroll-mt-24 text-2xl font-extrabold tracking-tight outline-none">{section.title}</h2>
          <p className="mt-1 text-muted">{section.text}</p>
          <HubGrid entries={section.entries} level={3} className="mt-4" />
        </section>
      ))}
    </div>
  );
}
