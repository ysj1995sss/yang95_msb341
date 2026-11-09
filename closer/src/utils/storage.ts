// Answers live only in this browser (localStorage). Private windows and blocked storage throw,
// so every read and write is wrapped: the page keeps working, it just doesn't remember.

export interface KeyValueStore {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
}

export interface SavedAnswer {
  text: string;
  savedAt: string;
}

const ANSWERS = "closer.answers";
const DAILY = "closer.daily";

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

export function loadAnswers(store: KeyValueStore | null = browserStore()): Record<string, SavedAnswer> {
  return read<Record<string, SavedAnswer>>(ANSWERS, store) ?? {};
}

/** Saves an answer; false when the browser won't keep it. */
export function saveAnswer(questionId: string, text: string, store: KeyValueStore | null = browserStore()): boolean {
  const answers = loadAnswers(store);
  answers[questionId] = { text, savedAt: new Date().toISOString() };
  return write(ANSWERS, answers, store);
}

export function loadDailyAnswer(
  dateKey: string,
  store: KeyValueStore | null = browserStore(),
): { questionId: string; text: string } | null {
  return read<Record<string, { questionId: string; text: string }>>(DAILY, store)?.[dateKey] ?? null;
}

export function saveDailyAnswer(
  dateKey: string,
  questionId: string,
  text: string,
  store: KeyValueStore | null = browserStore(),
): boolean {
  const all = read<Record<string, { questionId: string; text: string }>>(DAILY, store) ?? {};
  all[dateKey] = { questionId, text };
  return write(DAILY, all, store);
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
