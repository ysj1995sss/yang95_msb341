import { browserStore, read, write, type KeyValueStore } from "./storage";

/** One small remembered choice (theme, timer length, who's playing). Like favorites, it keeps working in
 *  memory when the browser refuses storage: the choice just isn't remembered next visit. */
export interface Setting<T> {
  get(): T;
  set(value: T): void;
  subscribe(listener: () => void): () => void;
}

export function createSetting<T>(
  key: string,
  fallback: T,
  isValid: (value: unknown) => value is T,
  store: KeyValueStore | null = browserStore(),
): Setting<T> {
  const stored = read<unknown>(key, store);
  let value: T = isValid(stored) ? stored : fallback;
  const listeners = new Set<() => void>();
  return {
    get: () => value,
    set(next) {
      if (next === value) return;
      value = next;
      write(key, next, store);
      listeners.forEach((l) => l());
    },
    subscribe(listener) {
      listeners.add(listener);
      return () => void listeners.delete(listener);
    },
  };
}
