import type { Depth } from "../types";
import { shuffle } from "./shuffle";

// Plans one round of trivia, or one set of Would You Rather and debates: which questions, in what order. A mixed round climbs from Easy to Expert;
// topics are spread out; questions not seen lately come first, and only when the new ones run out do
// older ones return, the longest-ago first.

export interface RoundItem { id: string; depth: Depth; topic: string; format?: string }

/** A mixed 10-question round: four Easy, three Medium, two Hard, one Expert. */
export const MIX: Record<Depth, number> = { 1: 4, 2: 3, 3: 2, 4: 1 };

/** How many of each difficulty a mixed round of `length` should have (shares of MIX, always adding up). */
export function mixFor(length: number, mix: Record<Depth, number> = MIX): Record<Depth, number> {
  const out: Record<Depth, number> = { 1: 0, 2: 0, 3: 0, 4: 0 };
  const exact = ([1, 2, 3, 4] as Depth[]).map((d) => ({ d, want: (mix[d] * length) / 10 }));
  for (const e of exact) out[e.d] = Math.floor(e.want);
  let left = length - exact.reduce((n, e) => n + out[e.d], 0);
  for (const e of [...exact].sort((a, b) => (b.want % 1) - (a.want % 1) || a.d - b.d)) if (left > 0) { out[e.d]++; left--; }
  return out;
}

/** New questions first (shuffled), then seen ones, longest ago first. */
function ranked<T extends RoundItem>(pool: readonly T[], seen: readonly string[], random?: () => number): { fresh: T[]; old: T[] } {
  const when = new Map(seen.map((id, i) => [id, i]));
  return {
    fresh: shuffle(pool.filter((q) => !when.has(q.id)), random),
    old: pool.filter((q) => when.has(q.id)).sort((a, b) => when.get(a.id)! - when.get(b.id)!),
  };
}

export const unseenCount = (pool: readonly RoundItem[], seen: readonly string[]): number => {
  const set = new Set(seen);
  return pool.filter((q) => !set.has(q.id)).length;
};

export function planRound<T extends RoundItem>(pool: readonly T[], options: {
  length: number; level?: Depth | "mix"; seen?: readonly string[]; random?: () => number; mix?: Record<Depth, number>;
}): T[] {
  const level = options.level ?? "mix";
  const usable = level === "mix" ? [...pool] : pool.filter((q) => q.depth === level);
  const { fresh, old } = ranked(usable, options.seen ?? [], options.random);
  const length = Math.min(options.length, usable.length);
  const chosen: T[] = [];
  const used = new Map<string, number>();
  const weight = (q: T) => (used.get(q.topic) ?? 0) + (used.get(`f:${q.format}`) ?? 0);
  /** Takes the next question from `from`, preferring the topic used least so far. */
  const take = (from: T[], ok: (q: T) => boolean, spread: boolean): boolean => {
    let best = -1;
    for (let i = 0; i < from.length; i++) {
      if (!ok(from[i]!)) continue;
      if (best < 0 || (spread && weight(from[i]!) < weight(from[best]!))) best = i;
      if (!spread) break;
    }
    if (best < 0) return false;
    const [q] = from.splice(best, 1) as [T];
    chosen.push(q);
    used.set(q.topic, (used.get(q.topic) ?? 0) + 1);
    if (q.format) used.set(`f:${q.format}`, (used.get(`f:${q.format}`) ?? 0) + 1);
    return true;
  };

  if (level === "mix") {
    const want = mixFor(length, options.mix);
    for (const d of [4, 3, 2, 1] as Depth[]) for (let n = 0; n < want[d]; n++) {
      // A new question of this difficulty; failing that a new one of the nearest difficulty.
      const near = ([1, 2, 3, 4] as Depth[]).sort((a, b) => Math.abs(a - d) - Math.abs(b - d) || a - b);
      if (!near.some((x) => take(fresh, (q) => q.depth === x, true))) near.some((x) => take(old, (q) => q.depth === x, false));
    }
  }
  while (chosen.length < length && (take(fresh, () => true, true) || take(old, () => true, false)));
  return inOrder(chosen);
}

/** Easiest first, without two questions on the same topic in a row where that can be avoided. */
function inOrder<T extends RoundItem>(items: T[]): T[] {
  const left = [...items].sort((a, b) => a.depth - b.depth);
  const out: T[] = [];
  while (left.length) {
    const last = out.at(-1);
    const level = (q: T) => q.depth === left[0]!.depth;
    let i = left.findIndex((q) => level(q) && q.topic !== last?.topic && (!q.format || q.format !== last?.format));
    if (i < 0) i = left.findIndex((q) => level(q) && q.topic !== last?.topic);
    if (i < 0) i = 0;
    out.push(...left.splice(i, 1));
  }
  return out;
}
