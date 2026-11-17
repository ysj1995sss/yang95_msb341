import { shuffle } from "../shuffle";

// Higher or Lower: a fact is shown with its number; the player guesses whether a second one is higher
// or lower. Numbers always come from one group (heights, planet sizes, years…), so they compare.

export interface Fact {
  name: string;
  value: number;
}

export interface FactGroup {
  id: string;
  /** "How tall is it?" */
  question: string;
  unit: string;
  /** What "higher" and "lower" mean here: "taller" / "shorter", "later" / "earlier". */
  higher: string;
  lower: string;
  facts: readonly Fact[];
}

export type Guess = "higher" | "lower";

export const isRight = (guess: Guess, known: Fact, other: Fact): boolean =>
  guess === "higher" ? other.value > known.value : other.value < known.value;

/** Two facts with different numbers, from one group. */
export function pickPair(group: FactGroup, random: () => number = Math.random): [Fact, Fact] {
  const facts = shuffle(group.facts, random);
  const known = facts[0]!;
  const other = facts.find((f) => f.value !== known.value);
  if (!other) throw new Error(`Group ${group.id} needs at least two different numbers`);
  return [known, other];
}

/** "8,849 m", or just "1876" for a year. */
export const formatValue = (value: number, unit: string): string =>
  unit === "year" ? String(value) : `${value.toLocaleString("en-US")} ${unit}`;
