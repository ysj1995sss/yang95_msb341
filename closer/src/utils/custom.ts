import type { Depth, OpenQuestion } from "../types";
import { browserStore, read, write, type KeyValueStore } from "./storage";

// "My questions": questions a person writes themselves, kept only on this device (localStorage).

export interface CustomQuestion {
  id: string;
  text: string;
  depth: Depth;
  createdAt: string;
}

export const MAX_CUSTOM = 100;
export const MIN_LENGTH = 8;
export const MAX_LENGTH = 200;

const KEY = "closer.custom";

export type AddResult = { ok: true; question: CustomQuestion } | { ok: false; reason: string };

export interface CustomStore {
  get(): readonly CustomQuestion[];
  add(text: string, depth: Depth): AddResult;
  remove(id: string): void;
  subscribe(listener: () => void): () => void;
}

const normal = (text: string) => text.trim().replace(/\s+/g, " ").toLowerCase();
const isDepth = (d: unknown): d is Depth => d === 1 || d === 2 || d === 3 || d === 4;

function isCustom(value: unknown): value is CustomQuestion {
  const v = value as Partial<CustomQuestion> | null;
  return !!v && typeof v.id === "string" && typeof v.text === "string" && isDepth(v.depth) && typeof v.createdAt === "string";
}

export function createCustomStore(store: KeyValueStore | null = browserStore(), now: () => Date = () => new Date()): CustomStore {
  const saved = read<unknown>(KEY, store);
  let list: readonly CustomQuestion[] = Array.isArray(saved) ? saved.filter(isCustom) : [];
  // Ids carry the time they were made, so a removed question's id is never given to a new one
  // (a favorite saved for the old question can't land on the new one).
  let counter = 0;
  const listeners = new Set<() => void>();
  const commit = (next: readonly CustomQuestion[]) => {
    list = next;
    write(KEY, list, store);
    listeners.forEach((l) => l());
  };

  return {
    get: () => list,
    add(text, depth) {
      const clean = text.trim().replace(/\s+/g, " ");
      if (clean.length < MIN_LENGTH) return { ok: false, reason: `Write at least ${MIN_LENGTH} characters.` };
      if (clean.length > MAX_LENGTH) return { ok: false, reason: `Keep it under ${MAX_LENGTH} characters.` };
      if (list.length >= MAX_CUSTOM) return { ok: false, reason: `You can keep up to ${MAX_CUSTOM} questions. Remove one to add another.` };
      if (list.some((q) => normal(q.text) === normal(clean))) return { ok: false, reason: "You already have that question." };
      counter += 1;
      const when = now();
      const question: CustomQuestion = { id: `mine-${when.getTime().toString(36)}-${counter}`, text: clean, depth, createdAt: when.toISOString() };
      commit([...list, question]);
      return { ok: true, question };
    },
    remove(id) {
      if (list.some((q) => q.id === id)) commit(list.filter((q) => q.id !== id));
    },
    subscribe(listener) {
      listeners.add(listener);
      return () => void listeners.delete(listener);
    },
  };
}

export const customQuestions = createCustomStore();

export const toOpenQuestion = (q: CustomQuestion): OpenQuestion => ({ id: q.id, categoryId: "mine", kind: "open", depth: q.depth, text: q.text });
