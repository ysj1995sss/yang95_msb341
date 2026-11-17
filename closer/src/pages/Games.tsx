import { Mic, Shuffle, Users } from "lucide-react";
import { HubGrid, type HubEntry } from "../components/HubCard";
import { questions } from "../data/questions";
import { href } from "../utils/router";

const games: HubEntry[] = [
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

/** The ways to play together: one page for the games, instead of three links in the menu. */
export function Games() {
  return (
    <div className="mx-auto max-w-5xl px-4 pt-10 sm:px-6 sm:pt-14">
      <h1 tabIndex={-1} className="text-4xl font-extrabold tracking-tight sm:text-5xl">Games</h1>
      <p className="mt-3 max-w-2xl text-lg text-muted">Play together on one phone or one screen. Nothing to sign up for, nothing to type.</p>
      <HubGrid entries={games} />
    </div>
  );
}
