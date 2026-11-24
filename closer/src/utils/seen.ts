import { browserStore, read, write, type KeyValueStore } from "./storage";

// Which questions were asked recently on this device, oldest first, so rounds stop repeating
// themselves. It outlives a visit (a new visit starts a new round, not a new memory).

export interface SeenLog {
  all(): readonly string[];
  /** Moves a question to the "just seen" end. */
  add(id: string): void;
  /** Forgets these, so they count as new again. */
  forget(ids: readonly string[]): void;
}

export function createSeenLog(key: string, store: KeyValueStore | null = browserStore(), keep = 2500): SeenLog {
  const load = (): string[] => {
    const saved = read<unknown>(key, store);
    return Array.isArray(saved) ? saved.filter((x): x is string => typeof x === "string") : [];
  };
  let ids = load();
  const save = (next: string[]) => { ids = next.slice(-keep); write(key, ids, store); };
  return {
    all: () => ids,
    add: (id) => save([...ids.filter((x) => x !== id), id]),
    forget: (gone) => { const drop = new Set(gone); save(ids.filter((x) => !drop.has(x))); },
  };
}

export const triviaSeen = createSeenLog("closer.trivia.seen");
export const choicesSeen = createSeenLog("closer.choices.seen");
