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
