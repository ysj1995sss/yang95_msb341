import { Mic, Shuffle, Users } from "lucide-react";
import { HubGrid, type HubEntry } from "../components/HubCard";
import { gameGroups, games } from "../data/games";
import { questions } from "../data/questions";
import { href } from "../utils/router";

const questionGames: HubEntry[] = [
  {
    title: "Guess My Answer", detail: "2 to 6 players", to: href.guess, cta: "Play", icon: Users, tint: "lavender", gradient: "from-plum-600 to-coral-500",
    text: "One person secretly picks an answer, the device is passed around, and everyone else guesses. Right guesses score.",
  },
  {
    title: "Debate Night", detail: "2 players and a room", to: href.debate, cta: "Play", icon: Mic, tint: "peach", gradient: "from-plum-500 to-sky-400",
    text: "Two sides, a speaking clock for each, and the room votes on who argued better.",
  },
  {
    title: "Surprise me", detail: "1 or more", to: href.surprise, cta: "Shuffle", icon: Shuffle, tint: "rose", gradient: "from-coral-500 to-plum-500",
    text: `One shuffled round through all ${questions.length} questions. No experience to pick.`,
  },
];

const sections = [
  ...gameGroups.map((group) => ({
    id: group.id, title: group.title, text: group.text,
    entries: games.filter((g) => g.group === group.id).map<HubEntry>((g) => ({
      title: g.title, detail: g.players, text: g.text, to: href.game(g.id), cta: "Play", icon: g.icon, gradient: g.gradient, tint: g.tint,
    })),
  })),
  { id: "questions", title: "Question games", text: "Built on the question library.", entries: questionGames },
];

/** The ways to play together: every game, in groups, on one page. */
export function Games() {
  return (
    <div className="mx-auto max-w-5xl px-4 pb-4 pt-10 sm:px-6 sm:pt-14">
      <h1 tabIndex={-1} className="text-4xl font-extrabold tracking-tight sm:text-5xl">Games</h1>
      <p className="mt-3 max-w-2xl text-lg text-muted">
        {games.length + questionGames.length} games to play together on one phone or one screen. Nothing to sign up for, and names are never saved.
      </p>
      {sections.map((section) => (
        <section key={section.id} aria-labelledby={`games-${section.id}`} className="mt-10">
          <h2 id={`games-${section.id}`} className="text-2xl font-extrabold tracking-tight">{section.title}</h2>
          <p className="mt-1 text-muted">{section.text}</p>
          <HubGrid entries={section.entries} level={3} className="mt-4" />
        </section>
      ))}
    </div>
  );
}
