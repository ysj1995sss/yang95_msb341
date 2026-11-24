import type { AudienceChoice, ChoiceTopicId, Depth, OpenQuestion, Question } from "../types";
import { createSetting } from "./settings";
import { planRound } from "./triviaRound";

// Would You Rather & Debates: which prompts fit what people chose, and the order of one set.

export type Format = "both" | "would-you-rather" | "debate";
export type TopicChoice = "all" | ChoiceTopicId;

const formats: readonly Format[] = ["both", "would-you-rather", "debate"];
const topicIds: readonly TopicChoice[] = ["all", "funny", "food", "travel", "bonds", "money", "pop", "future", "ethics", "society", "powers"];

export const formatSetting = createSetting<Format>("closer.choices.format", "both", (v): v is Format => formats.includes(v as Format));
export const choiceTopicSetting = createSetting<TopicChoice>("closer.choices.topic", "all", (v): v is TopicChoice => topicIds.includes(v as TopicChoice));
/** The deepest intensity allowed, or 0 for "whatever suits the group". */
export const ceilingSetting = createSetting<Depth | 0>("closer.choices.ceiling", 0, (v): v is Depth | 0 => [0, 1, 2, 3, 4].includes(v as number));

/** How deep to go when nobody has said: teams and families start gently, and Bold is always opt-in. */
export const defaultCeiling = (audience: AudienceChoice): Depth => (audience === "team" || audience === "family" ? 2 : 3);

export interface ChoiceFilter { format: Format; topic: TopicChoice; ceiling: Depth }

/** The prompts that match. `pool` is already narrowed to the group playing. */
export function matchChoices(pool: readonly Question[], f: ChoiceFilter): OpenQuestion[] {
  return pool.filter((q): q is OpenQuestion =>
    q.kind === "open" && q.depth <= f.ceiling
    && (f.format === "both" || q.categoryId === f.format)
    && (f.topic === "all" || q.topic === f.topic));
}

/** How a set is spread across the intensities allowed (tenths): mostly approachable, deepening gradually. */
const MIXES: Record<Depth, Record<Depth, number>> = {
  1: { 1: 10, 2: 0, 3: 0, 4: 0 },
  2: { 1: 6, 2: 4, 3: 0, 4: 0 },
  3: { 1: 4, 2: 4, 3: 2, 4: 0 },
  4: { 1: 3, 2: 3, 3: 2, 4: 2 },
};

export function planChoices(pool: readonly OpenQuestion[], options: { length: number; ceiling: Depth; seen: readonly string[]; random?: () => number }): string[] {
  const items = pool.map((q) => ({ id: q.id, depth: q.depth, topic: q.topic ?? "other", format: q.categoryId }));
  return planRound(items, { length: options.length, seen: options.seen, random: options.random, mix: MIXES[options.ceiling] }).map((q) => q.id);
}
