import type { PlaySet } from "../data/playSets";
import { restoreSession } from "./session";
import { browserStore, loadSession, read, write, type KeyValueStore } from "./storage";

// Where someone is in a round, and which set they played last, so the home page and the Explore
// cards can show progress and offer "Continue".

export interface RoundProgress {
  done: number;
  total: number;
  finished: boolean;
}

/** The `categoryId` a set's saved session is checked against (the category, or "mixed"). */
export const scopeOf = (set: PlaySet): string => set.category?.id ?? "mixed";

/** How far through its round a saved session is, or null when nothing (usable) was saved. */
export function roundProgress(saved: unknown, set: PlaySet): RoundProgress | null {
  if (set.pool.length === 0) return null;
  const state = restoreSession(saved, scopeOf(set), set.pool, set.limit);
  if (!state) return null;
  const total = set.limit ?? set.pool.length;
  return { done: Math.min(state.seen.length, total), total, finished: state.done };
}

export function savedProgress(set: PlaySet, store: KeyValueStore | null = browserStore()): RoundProgress | null {
  return roundProgress(loadSession(set.key, store), set);
}

const LAST = "closer.last";

export function loadLastPlayed(store: KeyValueStore | null = browserStore()): string | null {
  const value = read<unknown>(LAST, store);
  return typeof value === "string" ? value : null;
}

export function saveLastPlayed(key: string, store: KeyValueStore | null = browserStore()): void {
  write(LAST, key, store);
}
