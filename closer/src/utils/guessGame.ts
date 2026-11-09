import type { GuessQuestion } from "../types";
import { shuffle } from "./shuffle";

// Guess My Answer: two people share one device. Each round one person (the answerer) secretly
// picks the option that fits them best, the other (the guesser) guesses it, and a matching guess
// scores a point. Roles swap every round. The secret is only readable in the "reveal" phase.

export type Phase = "handoff-answer" | "answering" | "handoff-guess" | "guessing" | "reveal" | "final";

export interface GuessState {
  players: [string, string];
  questions: GuessQuestion[];
  round: number;
  phase: Phase;
  secret: number | null;
  guess: number | null;
  scores: [number, number];
}

export const answererOf = (round: number): 0 | 1 => (round % 2 === 0 ? 0 : 1);
export const guesserOf = (round: number): 0 | 1 => (round % 2 === 0 ? 1 : 0);

export function startGame(
  players: [string, string],
  pool: readonly GuessQuestion[],
  rounds: number,
  random?: () => number,
): GuessState {
  const questions = shuffle(pool, random).slice(0, Math.min(rounds, pool.length));
  return { players, questions, round: 0, phase: "handoff-answer", secret: null, guess: null, scores: [0, 0] };
}

/** The answerer has the device and is ready. */
export function beginAnswering(s: GuessState): GuessState {
  return s.phase === "handoff-answer" ? { ...s, phase: "answering" } : s;
}

/** Locks in the secret answer and hides it behind the hand-off screen. */
export function lockAnswer(s: GuessState, option: number): GuessState {
  if (s.phase !== "answering" || !isOption(s, option)) return s;
  return { ...s, secret: option, phase: "handoff-guess" };
}

/** The guesser has the device and is ready. */
export function beginGuessing(s: GuessState): GuessState {
  return s.phase === "handoff-guess" ? { ...s, phase: "guessing" } : s;
}

/** Submits the guess and reveals. Only the first submit in a round scores. */
export function submitGuess(s: GuessState, option: number): GuessState {
  if (s.phase !== "guessing" || s.secret === null || !isOption(s, option)) return s;
  const scores: [number, number] = [...s.scores];
  if (option === s.secret) scores[guesserOf(s.round)] += 1;
  return { ...s, guess: option, scores, phase: "reveal" };
}

/** After the reveal: the next round, or the final scores. */
export function nextRound(s: GuessState): GuessState {
  if (s.phase !== "reveal") return s;
  const round = s.round + 1;
  if (round >= s.questions.length) return { ...s, round, phase: "final", secret: null, guess: null };
  return { ...s, round, phase: "handoff-answer", secret: null, guess: null };
}

/** Same players and theme, fresh shuffle and zeroed scores. */
export function replay(s: GuessState, pool: readonly GuessQuestion[], random?: () => number): GuessState {
  return startGame(s.players, pool, s.questions.length, random);
}

export function winner(s: GuessState): 0 | 1 | "tie" {
  return s.scores[0] === s.scores[1] ? "tie" : s.scores[0] > s.scores[1] ? 0 : 1;
}

function isOption(s: GuessState, option: number): boolean {
  return Number.isInteger(option) && option >= 0 && option < (s.questions[s.round]?.options.length ?? 0);
}
