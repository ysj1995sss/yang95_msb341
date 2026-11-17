import { questions } from "../questions";
import type { Depth, TriviaQuestion } from "../../types";
import { moreDuelQuestions } from "./brainMore";
import { mergeUnique } from "./merge";

// Which library questions the party games borrow. Truth and Pass the Bomb want questions that are
// about the person, so the two groups that are about opinions to argue over are left out.

export type Spice = "light" | "medium" | "bold";

export const spiceLabels: Record<Spice, string> = {
  light: "Light and fun",
  medium: "A bit more personal",
  bold: "Anything goes",
};

const deepest: Record<Spice, Depth> = { light: 1, medium: 2, bold: 4 };

const skipped = new Set(["debate", "would-you-rather"]);

/** Open questions from the library no deeper than the chosen spice. */
export function truthPool(spice: Spice): string[] {
  return questions.flatMap((q) => (q.kind === "open" && !skipped.has(q.categoryId) && q.depth <= deepest[spice] ? [q.text] : []));
}

/** Trivia from the library, for the Trivia Duel. */
const libraryTrivia = questions.flatMap((q) => (q.kind === "trivia" ? [q] : []));
const extraTrivia: TriviaQuestion[] = moreDuelQuestions.map(({ difficulty, ...rest }, i) => ({
  ...rest, id: `duel-${i + 1}`, categoryId: "trivia", kind: "trivia", depth: difficulty,
}));
export const duelQuestions: TriviaQuestion[] = mergeUnique((q) => q.text, libraryTrivia, extraTrivia);
