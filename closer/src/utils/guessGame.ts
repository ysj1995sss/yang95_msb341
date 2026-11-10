import type { GuessQuestion } from "../types";
import { shuffle } from "./shuffle";

// Guess My Answer: two to six people share one device. Each round one person (the answerer) secretly
// picks the option that fits them best. Then everyone else takes the device in turn and guesses it,
// without seeing each other's guesses. Each right guess scores a point. The answerer rotates every
// round. With two players that is simply "one answers, the other guesses, then swap". The secret
// is only readable in the "reveal" phase.

export type Phase = "handoff-answer" | "answering" | "handoff-guess" | "guessing" | "reveal" | "final";

export const MIN_PLAYERS = 2;
export const MAX_PLAYERS = 6;

export interface GuessState {
  players: string[];
  questions: GuessQuestion[];
  round: number;
  phase: Phase;
  secret: number | null;
  /** Which of this round's guessers has the device (an index into `guessersOf(round, players.length)`). */
  turn: number;
  /** This round's guesses, by player (null for the answerer, and for anyone yet to guess). */
  guesses: (number | null)[];
  scores: number[];
}

/** Who answers in a round: the players take turns in seat order. */
export const answererOf = (round: number, players: number): number => round % players;

/** Who guesses in a round, in the order they take the device: everyone but the answerer, starting after them. */
export function guessersOf(round: number, players: number): number[] {
  const answerer = answererOf(round, players);
  return Array.from({ length: players - 1 }, (_, i) => (answerer + 1 + i) % players);
}

/** A game where everyone answers `each` times. */
export const totalRounds = (players: number, each: number): number => players * each;

const blankGuesses = (players: number): (number | null)[] => Array.from({ length: players }, () => null);

export function startGame(
  players: string[],
  pool: readonly GuessQuestion[],
  rounds: number,
  random?: () => number,
): GuessState {
  if (players.length < MIN_PLAYERS || players.length > MAX_PLAYERS) {
    throw new Error(`Guess My Answer needs ${MIN_PLAYERS} to ${MAX_PLAYERS} players.`);
  }
  const questions = shuffle(pool, random).slice(0, Math.min(rounds, pool.length));
  return {
    players,
    questions,
    round: 0,
    phase: "handoff-answer",
    secret: null,
    turn: 0,
    guesses: blankGuesses(players.length),
    scores: players.map(() => 0),
  };
}

/** The guesser whose turn it is. */
export const currentGuesser = (s: GuessState): number => guessersOf(s.round, s.players.length)[s.turn];

/** The answerer has the device and is ready. */
export function beginAnswering(s: GuessState): GuessState {
  return s.phase === "handoff-answer" ? { ...s, phase: "answering" } : s;
}

/** Locks in the secret answer and hides it behind the hand-off screen. */
export function lockAnswer(s: GuessState, option: number): GuessState {
  if (s.phase !== "answering" || !isOption(s, option)) return s;
  return { ...s, secret: option, turn: 0, phase: "handoff-guess" };
}

/** The next guesser has the device and is ready. */
export function beginGuessing(s: GuessState): GuessState {
  return s.phase === "handoff-guess" ? { ...s, phase: "guessing" } : s;
}

/** Takes the current guesser's guess. The next guesser gets the device; after the last guess the
 *  round is revealed and every right guess scores. Nothing is scored before the reveal. */
export function submitGuess(s: GuessState, option: number): GuessState {
  if (s.phase !== "guessing" || s.secret === null || !isOption(s, option)) return s;
  const guessers = guessersOf(s.round, s.players.length);
  const guesses = [...s.guesses];
  guesses[guessers[s.turn]] = option;
  if (s.turn + 1 < guessers.length) return { ...s, guesses, turn: s.turn + 1, phase: "handoff-guess" };
  const scores = [...s.scores];
  for (const g of guessers) if (guesses[g] === s.secret) scores[g] += 1;
  return { ...s, guesses, scores, phase: "reveal" };
}

/** After the reveal: the next round, or the final scores. */
export function nextRound(s: GuessState): GuessState {
  if (s.phase !== "reveal") return s;
  const round = s.round + 1;
  const fresh = { secret: null, turn: 0, guesses: blankGuesses(s.players.length) };
  if (round >= s.questions.length) return { ...s, ...fresh, round, phase: "final" };
  return { ...s, ...fresh, round, phase: "handoff-answer" };
}

/** Same players and settings, fresh shuffle and zeroed scores. */
export function replay(s: GuessState, pool: readonly GuessQuestion[], random?: () => number): GuessState {
  return startGame(s.players, pool, s.questions.length, random);
}

/** Everyone with the top score: one winner, or several in a tie. */
export function winners(s: GuessState): number[] {
  const best = Math.max(...s.scores);
  return s.scores.flatMap((score, i) => (score === best ? [i] : []));
}

function isOption(s: GuessState, option: number): boolean {
  return Number.isInteger(option) && option >= 0 && option < (s.questions[s.round]?.options.length ?? 0);
}
