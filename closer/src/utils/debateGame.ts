import { shuffle } from "./shuffle";

// Debate Night: two people share a device. Each round has a statement; one argues for it and the
// other against, each for the same time, and the room votes on who argued better. Sides swap every
// round, so each person defends both.

export type DebatePhase = "brief" | "for" | "against" | "vote" | "result" | "final";
export type Verdict = "for" | "against" | "draw";

export interface DebateState {
  players: [string, string];
  /** One statement per round, in order. */
  motions: string[];
  /** Spare statements, for swapping a round's statement when it doesn't suit. */
  spare: string[];
  round: number;
  phase: DebatePhase;
  /** How long each person speaks, in seconds. */
  seconds: number;
  scores: [number, number];
  verdict: Verdict | null;
}

export const forPlayerOf = (round: number): 0 | 1 => (round % 2 === 0 ? 0 : 1);
export const againstPlayerOf = (round: number): 0 | 1 => (round % 2 === 0 ? 1 : 0);

export function startDebate(
  players: [string, string],
  pool: readonly string[],
  rounds: number,
  seconds: number,
  random?: () => number,
): DebateState {
  const all = shuffle(pool, random);
  const count = Math.min(rounds, all.length);
  return {
    players,
    motions: all.slice(0, count),
    spare: all.slice(count),
    round: 0,
    phase: "brief",
    seconds,
    scores: [0, 0],
    verdict: null,
  };
}

/** The sides are set and the first speaker (the "for" side) takes the floor. */
export function beginSpeeches(s: DebateState): DebateState {
  return s.phase === "brief" ? { ...s, phase: "for" } : s;
}

/** The "for" speech is over and the other side speaks; after that, the room votes. */
export function nextSpeaker(s: DebateState): DebateState {
  if (s.phase === "for") return { ...s, phase: "against" };
  if (s.phase === "against") return { ...s, phase: "vote" };
  return s;
}

/** The room's verdict. Only the first vote in a round counts. */
export function castVote(s: DebateState, verdict: Verdict): DebateState {
  if (s.phase !== "vote") return s;
  const scores: [number, number] = [...s.scores];
  if (verdict === "for") scores[forPlayerOf(s.round)] += 1;
  if (verdict === "against") scores[againstPlayerOf(s.round)] += 1;
  return { ...s, scores, verdict, phase: "result" };
}

export function nextRound(s: DebateState): DebateState {
  if (s.phase !== "result") return s;
  const round = s.round + 1;
  if (round >= s.motions.length) return { ...s, round, phase: "final", verdict: null };
  return { ...s, round, phase: "brief", verdict: null };
}

/** Swaps this round's statement for a spare one (before anyone has spoken). */
export function reroll(s: DebateState): DebateState {
  if (s.phase !== "brief" || s.spare.length === 0) return s;
  const [next, ...spare] = s.spare;
  const motions = [...s.motions];
  motions[s.round] = next;
  return { ...s, motions, spare };
}

/** Same people and settings, fresh statements and zeroed scores. */
export function replay(s: DebateState, pool: readonly string[], random?: () => number): DebateState {
  return startDebate(s.players, pool, s.motions.length, s.seconds, random);
}

export function winner(s: DebateState): 0 | 1 | "tie" {
  return s.scores[0] === s.scores[1] ? "tie" : s.scores[0] > s.scores[1] ? 0 : 1;
}
