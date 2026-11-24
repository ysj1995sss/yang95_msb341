import type { PlaySet } from "../data/playSets";
import { restoreSession } from "./session";
import { browserStore, loadSession, read, SESSION_PREFIX, write, type KeyValueStore, type RemovableStore } from "./storage";

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
  const total = set.limit === null ? set.pool.length : Math.min(set.limit, state.order.length);
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

/** Forgets every saved round and the "last played" pointer, so the next round of each set is a fresh shuffle.
 *  Favorites and the person's own questions are not touched. */
export function clearSavedRounds(store: RemovableStore | null = browserStore()): void {
  if (!store) return;
  try {
    const keys: string[] = [];
    for (let i = 0; i < store.length; i++) {
      const key = store.key(i);
      if (key !== null && (key === LAST || key.startsWith(SESSION_PREFIX))) keys.push(key);
    }
    keys.forEach((key) => store.removeItem(key));
  } catch {
    // Blocked storage: nothing was saved, so nothing needs clearing.
  }
}
