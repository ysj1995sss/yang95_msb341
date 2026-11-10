import type { CategoryId, OpenEntry, OpenQuestion, Question, TriviaQuestion } from "../types";
import { debate } from "./library/debate";
import { deep } from "./library/deep";
import { family } from "./library/family";
import { icebreakers } from "./library/icebreakers";
import { imagination } from "./library/imagination";
import { love } from "./library/love";
import { party } from "./library/party";
import { storytelling } from "./library/storytelling";
import { trivia } from "./library/trivia";
import { wouldYouRather } from "./library/wouldYouRather";

/** The library: 10 categories of 50 questions. A question's id is its category and its place in that
 *  category's file ("love-7"), so ids stay the same as long as nothing is inserted above them. */
const open: Record<Exclude<CategoryId, "trivia">, OpenEntry[]> = {
  love,
  deep,
  party,
  debate,
  family,
  icebreakers,
  "would-you-rather": wouldYouRather,
  imagination,
  storytelling,
};

const openQuestions: OpenQuestion[] = (Object.keys(open) as (keyof typeof open)[]).flatMap((categoryId) =>
  open[categoryId].map(([depth, text], i) => ({
    id: `${categoryId}-${i + 1}`,
    categoryId,
    kind: "open" as const,
    depth,
    text,
  })),
);

const triviaQuestions: TriviaQuestion[] = trivia.map(({ difficulty, ...rest }, i) => ({
  ...rest,
  id: `trivia-${i + 1}`,
  categoryId: "trivia",
  kind: "trivia",
  depth: difficulty,
}));

export const questions: Question[] = [...openQuestions, ...triviaQuestions];

const byId = new Map(questions.map((q) => [q.id, q]));

export const questionsFor = (categoryId: CategoryId): Question[] =>
  questions.filter((q) => q.categoryId === categoryId);

export const questionById = (id: string): Question | undefined => byId.get(id);
