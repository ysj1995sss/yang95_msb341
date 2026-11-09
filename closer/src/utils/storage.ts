// Favorites and small bits of state live only in this browser (localStorage). Private windows and
// blocked storage throw, so every read and write is wrapped: the page keeps working, it just
// doesn't remember.

export interface KeyValueStore {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
}

const DAILY_REVEALED = "closer.daily.revealed";

function browserStore(): KeyValueStore | null {
  try {
    return typeof window !== "undefined" ? window.localStorage : null;
  } catch {
    return null;
  }
}

function read<T>(key: string, store: KeyValueStore | null): T | null {
  try {
    const raw = store?.getItem(key);
    return raw ? (JSON.parse(raw) as T) : null;
  } catch {
    return null;
  }
}

function write(key: string, value: unknown, store: KeyValueStore | null): boolean {
  try {
    if (!store) return false;
    store.setItem(key, JSON.stringify(value));
    return true;
  } catch {
    return false;
  }
}

/** Whether today's question was already revealed on this device (so a refresh doesn't hide it again). */
export function loadDailyRevealed(dateKey: string, store: KeyValueStore | null = browserStore()): boolean {
  return read<string>(DAILY_REVEALED, store) === dateKey;
}

export function saveDailyRevealed(dateKey: string, store: KeyValueStore | null = browserStore()): void {
  write(DAILY_REVEALED, dateKey, store);
}

// ---- Favorites -------------------------------------------------------------------------------
// Hearted question ids, kept in localStorage. When the browser refuses storage the hearts still
// work for the visit (held in memory) and simply aren't remembered.

const FAVORITES = "closer.favorites";
const SESSION_PREFIX = "closer.session.";

export interface FavoritesStore {
  get(): readonly string[];
  has(id: string): boolean;
  /** Adds or removes `id`; returns whether it is now a favorite. */
  toggle(id: string): boolean;
  subscribe(listener: () => void): () => void;
}

export function createFavoritesStore(store: KeyValueStore | null = browserStore()): FavoritesStore {
  const stored = read<unknown>(FAVORITES, store);
  let ids: readonly string[] = Array.isArray(stored)
    ? [...new Set(stored.filter((x): x is string => typeof x === "string"))]
    : [];
  const listeners = new Set<() => void>();
  return {
    get: () => ids,
    has: (id) => ids.includes(id),
    toggle(id) {
      const now = !ids.includes(id);
      ids = now ? [...ids, id] : ids.filter((x) => x !== id);
      write(FAVORITES, ids, store);
      listeners.forEach((l) => l());
      return now;
    },
    subscribe(listener) {
      listeners.add(listener);
      return () => void listeners.delete(listener);
    },
  };
}

export const favorites = createFavoritesStore();

// ---- Session progress ------------------------------------------------------------------------
// A category round survives a refresh while the tab stays open (sessionStorage).

function sessionStore(): KeyValueStore | null {
  try {
    return typeof window !== "undefined" ? window.sessionStorage : null;
  } catch {
    return null;
  }
}

export function loadSession(key: string, store: KeyValueStore | null = sessionStore()): unknown {
  return read<unknown>(SESSION_PREFIX + key, store);
}

export function saveSession(key: string, state: unknown, store: KeyValueStore | null = sessionStore()): boolean {
  return write(SESSION_PREFIX + key, state, store);
}

export function clearSession(key: string, store: KeyValueStore | null = sessionStore()): void {
  write(SESSION_PREFIX + key, null, store);
}
