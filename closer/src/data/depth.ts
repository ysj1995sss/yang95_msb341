import type { CategoryId, Depth } from "../types";

export interface LevelInfo {
  name: string;
  hint: string;
}

export const DEPTHS: readonly Depth[] = [1, 2, 3, 4];

/** Conversation categories: how personal the question gets. */
export const conversationLevels: Record<Depth, LevelInfo> = {
  1: { name: "Fun & Light", hint: "Entertaining and easy to answer" },
  2: { name: "Meaningful", hint: "Personal and connection-building" },
  3: { name: "Deep", hint: "Emotional and thought-provoking" },
  4: { name: "Bold", hint: "Daring or intimate. Always optional" },
};

/** Trivia: how hard the question is. */
export const quizLevels: Record<Depth, LevelInfo> = {
  1: { name: "Easy", hint: "Most people know this" },
  2: { name: "Medium", hint: "Takes a moment's thought" },
  3: { name: "Hard", hint: "A challenge for a quiz night" },
  4: { name: "Expert", hint: "For trivia champions" },
};

export const levelsFor = (categoryId: CategoryId): Record<Depth, LevelInfo> =>
  categoryId === "trivia" ? quizLevels : conversationLevels;
