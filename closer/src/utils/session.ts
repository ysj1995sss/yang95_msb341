import type { Depth } from "../types";
import { shuffle } from "./shuffle";

// A play session is plain data plus pure functions, so the rules (no repeats, skipped counts as
// seen, switching depth never re-asks a question) are tested without a browser.

export type Level = Depth | "mix";
/** "moved" is a question left on screen by a depth change: seen, but neither answered nor skipped. */
export type Outcome = "answered" | "skipped" | "moved" | "correct" | "incorrect";

/** The least the session needs to know about a question. */
export interface PoolItem {
  id: string;
  depth: Depth;
}

export interface SessionState {
  categoryId: string;
  level: Level;
  /** Every id in the pool, in this round's shuffled order. */
  order: string[];
  /** Questions that have been shown, oldest first. A shown question is never shown again. */
  seen: string[];
  outcomes: Record<string, Outcome>;
  currentId: string | null;
  /** True when nothing is left to ask at the chosen level (or the quiz length is reached). */
  done: boolean;
  /** Quiz length (trivia); null means the whole pool. */
  limit: number | null;
}

export interface StartOptions {
  level?: Level;
  limit?: number | null;
  random?: () => number;
}

export interface Progress {
  done: number;
  total: number;
}

export interface Summary {
  answered: number;
  skipped: number;
  correct: number;
  incorrect: number;
  /** Correct answers as a whole-number percentage of answered questions (0 when none answered). */
  percent: number;
}

const matches = (item: PoolItem | undefined, level: Level) => !!item && (level === "mix" || item.depth === level);

function nextUnseen(state: Pick<SessionState, "order" | "seen" | "level">, pool: PoolItem[]): string | null {
  const byId = new Map(pool.map((q) => [q.id, q]));
  const seen = new Set(state.seen);
  return state.order.find((id) => !seen.has(id) && matches(byId.get(id), state.level)) ?? null;
}

/** Settles `currentId`/`done` after anything that changes what is shown. */
function settle(state: SessionState, pool: PoolItem[]): SessionState {
  if (state.limit !== null && state.seen.length >= state.limit) {
    return { ...state, currentId: null, done: true };
  }
  const id = nextUnseen(state, pool);
  if (!id) return { ...state, currentId: null, done: true };
  return { ...state, currentId: id, done: false, seen: [...state.seen, id] };
}

export function startSession(categoryId: string, pool: PoolItem[], options: StartOptions = {}): SessionState {
  const base: SessionState = {
    categoryId,
    level: options.level ?? "mix",
    order: shuffle(pool.map((q) => q.id), options.random),
    seen: [],
    outcomes: {},
    currentId: null,
    done: false,
    limit: options.limit ?? null,
  };
  return settle(base, pool);
}

/** Records what happened to the current question. The first outcome wins: a question can't be
 *  scored twice, so submitting again earns nothing. A skip never overrides an answer. */
export function recordOutcome(state: SessionState, outcome: Outcome): SessionState {
  const id = state.currentId;
  if (!id || state.outcomes[id]) return state;
  return { ...state, outcomes: { ...state.outcomes, [id]: outcome } };
}

/** Moves on. A question left without an answer counts as skipped (and so as seen). */
export function advance(state: SessionState, pool: PoolItem[]): SessionState {
  if (!state.currentId) return state;
  return settle(recordOutcome(state, "skipped"), pool);
}

/** Moves on from a conversation question the group talked through: it counts as "answered", not skipped. */
export function discuss(state: SessionState, pool: PoolItem[]): SessionState {
  return advance(recordOutcome(state, "answered"), pool);
}

export const skip = advance;

/** Switches depth. The question on screen stays if it fits the new level; otherwise it is marked
 *  "moved" (seen, never scored or counted as skipped) and the next unseen question at the new level is shown. */
export function changeLevel(state: SessionState, pool: PoolItem[], level: Level): SessionState {
  if (level === state.level) return state;
  let next: SessionState = { ...state, level };
  const current = state.currentId ? pool.find((q) => q.id === state.currentId) : undefined;
  if (current && matches(current, level)) return next;
  if (state.currentId) next = recordOutcome(next, "moved");
  return settle({ ...next, currentId: null }, pool);
}

/** Progress at the chosen level: how many have been shown out of how many there are to see. */
export function progress(state: SessionState, pool: PoolItem[]): Progress {
  const byId = new Map(pool.map((q) => [q.id, q]));
  if (state.limit !== null) {
    const unseen = state.order.filter((id) => !state.seen.includes(id) && matches(byId.get(id), state.level)).length;
    return { done: state.seen.length, total: Math.min(state.limit, state.seen.length + unseen) };
  }
  const total = pool.filter((q) => matches(q, state.level)).length;
  const done = state.seen.filter((id) => matches(byId.get(id), state.level)).length;
  return { done, total };
}

/** Of the questions at each level, how many are still unseen (for "6 left" hints). */
export function remainingByLevel(state: SessionState, pool: PoolItem[]): Record<Depth, number> {
  const seen = new Set(state.seen);
  const counts: Record<Depth, number> = { 1: 0, 2: 0, 3: 0, 4: 0 };
  for (const q of pool) if (!seen.has(q.id)) counts[q.depth] += 1;
  return counts;
}

export function summarize(state: SessionState): Summary {
  const values = Object.values(state.outcomes);
  const correct = values.filter((o) => o === "correct").length;
  const incorrect = values.filter((o) => o === "incorrect").length;
  const answered = values.filter((o) => o === "answered").length + correct + incorrect;
  const skipped = values.filter((o) => o === "skipped").length;
  return { answered, skipped, correct, incorrect, percent: answered ? Math.round((correct / answered) * 100) : 0 };
}

/** The headline for a finished quiz. It uses the same base as the score (answered questions),
 *  so "4 of 8 right" and "50%" always agree. */
export function resultTitle(s: Summary): string {
  if (s.answered === 0) return "You skipped every question";
  return `You got ${s.correct} of ${s.answered} right`;
}

/** Rebuilds a saved session if it still fits the pool; otherwise null (start fresh). */
export function restoreSession(saved: unknown, categoryId: string, pool: PoolItem[], limit: number | null): SessionState | null {
  const s = saved as Partial<SessionState> | null;
  if (!s || typeof s !== "object" || s.categoryId !== categoryId || s.limit !== limit) return null;
  if (!Array.isArray(s.order) || !Array.isArray(s.seen) || typeof s.outcomes !== "object" || s.outcomes === null) return null;
  const ids = new Set(pool.map((q) => q.id));
  const order = s.order as string[];
  if (order.length !== ids.size || !order.every((id) => ids.has(id)) || new Set(order).size !== order.length) return null;
  if (!(s.seen as string[]).every((id) => ids.has(id))) return null;
  if (s.level !== "mix" && ![1, 2, 3, 4].includes(s.level as number)) return null;
  if (s.currentId !== null && s.currentId !== undefined && !ids.has(s.currentId)) return null;
  return {
    categoryId,
    level: s.level as Level,
    order,
    seen: s.seen as string[],
    outcomes: s.outcomes as Record<string, Outcome>,
    currentId: s.currentId ?? null,
    done: !!s.done,
    limit,
  };
}
