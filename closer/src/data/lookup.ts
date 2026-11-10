import type { Question } from "../types";
import { customQuestions, toOpenQuestion } from "../utils/custom";
import { categoryById } from "./categories";
import { packs, packQuestions } from "./packs";
import { questionById } from "./questions";

// Every kind of question has an id; this finds the question behind one, wherever it lives: the
// library, a seasonal pack, or the player's own list. (A favorite is just an id.)

const packIndex = new Map<string, { question: Question; packName: string }>(
  packs.flatMap((pack) => packQuestions(pack).map((question) => [question.id, { question, packName: pack.name }] as const)),
);

export function findQuestion(id: string): Question | undefined {
  const library = questionById(id);
  if (library) return library;
  const fromPack = packIndex.get(id);
  if (fromPack) return fromPack.question;
  const mine = customQuestions.get().find((q) => q.id === id);
  return mine ? toOpenQuestion(mine) : undefined;
}

/** "Love & Relationships", the pack's name, or "My question": where a question came from. */
export function sourceLabel(q: Question): string | undefined {
  if (q.categoryId === "pack") return packIndex.get(q.id)?.packName;
  if (q.categoryId === "mine") return "My question";
  return categoryById(q.categoryId)?.name;
}
