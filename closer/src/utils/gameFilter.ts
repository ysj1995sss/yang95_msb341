import type { GameMood } from "../data/games";
import type { KeyValueStore } from "./storage";
import { read, write } from "./storage";

// The quick filter at the top of the Games page: how many people are playing, and what they're in
// the mood for. Kept for the visit (sessionStorage), so going back to the Games page shows the same list.

export type PlayerChoice = "any" | "1" | "2" | "3-5" | "6+";
export type MoodChoice = "any" | GameMood;

export interface GameFilter {
  players: PlayerChoice;
  mood: MoodChoice;
}

export interface Filterable {
  min: number;
  max: number;
  moods: readonly GameMood[];
}

export const NO_FILTER: GameFilter = { players: "any", mood: "any" };

export const playerChoices: readonly { id: PlayerChoice; label: string }[] = [
  { id: "any", label: "Any number" },
  { id: "1", label: "Just me" },
  { id: "2", label: "2 of us" },
  { id: "3-5", label: "3 to 5" },
  { id: "6+", label: "6 or more" },
];

/** The group sizes each choice covers. */
const sizes: Record<Exclude<PlayerChoice, "any">, [number, number]> = { "1": [1, 1], "2": [2, 2], "3-5": [3, 5], "6+": [6, Infinity] };

/** Whether a game can be played by the chosen number of people (some size in the range fits the game). */
export function fitsPlayers(game: Filterable, choice: PlayerChoice): boolean {
  if (choice === "any") return true;
  const [low, high] = sizes[choice];
  return game.min <= high && game.max >= low;
}

export function fitsFilter(game: Filterable, filter: GameFilter): boolean {
  return fitsPlayers(game, filter.players) && (filter.mood === "any" || game.moods.includes(filter.mood));
}

export const isFiltered = (filter: GameFilter): boolean => filter.players !== "any" || filter.mood !== "any";

const KEY = "closer.gamesFilter";
const playerIds = new Set<string>(playerChoices.map((c) => c.id));
const moodIds = new Set<string>(["any", "quick", "silly", "competitive", "know", "date", "creative"]);

export function loadGameFilter(store: KeyValueStore | null): GameFilter {
  const saved = read<Partial<GameFilter>>(KEY, store);
  return {
    players: typeof saved?.players === "string" && playerIds.has(saved.players) ? saved.players : "any",
    mood: typeof saved?.mood === "string" && moodIds.has(saved.mood) ? saved.mood : "any",
  };
}

export function saveGameFilter(filter: GameFilter, store: KeyValueStore | null): void {
  write(KEY, filter, store);
}
