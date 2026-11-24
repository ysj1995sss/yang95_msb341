import type { CategoryId, OpenEntry, OpenQuestion, Question, TriviaQuestion } from "../types";
import { choiceBank, earlierTopic } from "./choices/bank";
import { debate } from "./library/debate";
import { deep } from "./library/deep";
import { family } from "./library/family";
import { icebreakers } from "./library/icebreakers";
import { imagination } from "./library/imagination";
import { love } from "./library/love";
import { party } from "./library/party";
import { storytelling } from "./library/storytelling";
import { trivia } from "./library/trivia";
import { triviaBank } from "./trivia/bank";
import { wouldYouRather } from "./library/wouldYouRather";

/** The library: ten groups of 50 questions, plus two banks (trivia, and Would You Rather and debates) (the app shows them as seven experiences, see categories.ts).
 *  A question's id is its group and its place in that group's file ("love-7"), so ids stay the same as long as nothing is inserted above them. */
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
    ...(earlierTopic(categoryId, i) ? { topic: earlierTopic(categoryId, i) } : {}),
  })),
);

const coreTrivia: TriviaQuestion[] = trivia.map(({ difficulty, ...rest }, i) => ({
  ...rest,
  id: `trivia-${i + 1}`,
  categoryId: "trivia",
  kind: "trivia",
  depth: difficulty,
}));

/** The 50 original trivia questions keep their ids (trivia-1 to trivia-50); the bank adds the rest. */
const triviaQuestions: TriviaQuestion[] = [...coreTrivia, ...triviaBank];

export const questions: Question[] = [...openQuestions, ...choiceBank, ...triviaQuestions];

/** Whether a question is in the Surprise me mix: everything except the two large banks, which would swamp the rest. */
export const inSurpriseMix = (q: Question): boolean => new RegExp(`^${q.categoryId}-\\d+$`).test(q.id);

const byId = new Map(questions.map((q) => [q.id, q]));

export const questionsFor = (categoryId: CategoryId): Question[] =>
  questions.filter((q) => q.categoryId === categoryId);

export const questionById = (id: string): Question | undefined => byId.get(id);
