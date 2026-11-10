import type { AudienceChoice, Category, Question } from "../types";
import { toOpenQuestion, type CustomQuestion } from "../utils/custom";
import { href } from "../utils/router";
import { isAudience, matchesAudience, AUDIENCES } from "./audience";
import { categoryById } from "./categories";
import { packById, packQuestions } from "./packs";
import { questions, questionsFor } from "./questions";
import { inTopicGroup, topicGroupById } from "./triviaTopics";

// A "play set" is something you can play through: a category (for one group, or one trivia topic),
// the surprise mix, a seasonal pack, or your own questions. Each has a stable key that names its saved
// progress, which is what lets the home page say "Continue: Love & Relationships, 14 of 50".



export const QUIZ_LENGTH = 10;

export interface PlaySet {
  key: string;
  title: string;
  description: string;
  href: string;
  /** The category being played, or null for a mixed set (surprise, packs, your own questions). */
  category: Category | null;
  pool: Question[];
  /** Quiz length for trivia; null plays the whole pool. */
  limit: number | null;
  /** Whether the optional countdown is offered (party games and debates). */
  timer: boolean;
}

const audienceLabel = (a: AudienceChoice) => AUDIENCES.find((x) => x.id === a)?.label.toLowerCase();

export function categoryKey(categoryId: string, audience: AudienceChoice = "everyone", topic = "all"): string {
  const parts = ["play", categoryId];
  if (categoryId === "trivia") { if (topic !== "all") parts.push(`t-${topic}`); }
  else if (isAudience(audience)) parts.push(audience);
  return parts.join(":");
}

export function categorySet(categoryId: string, audience: AudienceChoice = "everyone", topic = "all"): PlaySet | null {
  const category = categoryById(categoryId);
  if (!category) return null;
  const quiz = category.id === "trivia";
  const group = quiz && topic !== "all" ? topicGroupById(topic) : undefined;
  const pool = questionsFor(category.id).filter((q) => (quiz ? inTopicGroup(q, group ? topic : "all") : matchesAudience(q, audience)));
  const forGroup = !quiz && isAudience(audience) ? ` Showing the questions that suit ${audienceLabel(audience)}.` : "";
  return {
    key: categoryKey(category.id, audience, group ? topic : "all"),
    title: group ? `${category.name}: ${group.label}` : category.name,
    description: category.description + forGroup,
    href: href.play(category.id),
    category,
    pool,
    limit: quiz && pool.length > 0 ? Math.min(QUIZ_LENGTH, pool.length) : null,
    timer: category.id === "party" || category.id === "debate",
  };
}

export function surpriseSet(audience: AudienceChoice = "everyone"): PlaySet {
  const pool = questions.filter((q) => matchesAudience(q, audience));
  return {
    key: isAudience(audience) ? `surprise:${audience}` : "surprise",
    title: "Surprise me",
    description: `A random mix from all ${pool.length} questions, across every category.`,
    href: href.surprise,
    category: null,
    pool,
    limit: null,
    timer: false,
  };
}

export function packSet(packId: string): PlaySet | null {
  const pack = packById(packId);
  if (!pack) return null;
  return {
    key: `pack:${pack.id}`,
    title: pack.name,
    description: pack.blurb,
    href: href.pack(pack.id),
    category: null,
    pool: packQuestions(pack),
    limit: null,
    timer: false,
  };
}

export function mineSet(custom: readonly CustomQuestion[]): PlaySet {
  return {
    key: "mine",
    title: "My questions",
    description: "The questions you wrote, in a fresh order.",
    href: href.minePlay,
    category: null,
    pool: custom.map(toOpenQuestion),
    limit: null,
    timer: false,
  };
}

/** Rebuilds a set from the key its progress was saved under; null for a key that means nothing now. */
export function setFromKey(key: string, custom: readonly CustomQuestion[] = []): PlaySet | null {
  const [kind, id, ...rest] = key.split(":");
  if (kind === "surprise") return surpriseSet(isAudience(id) ? id : "everyone");
  if (kind === "pack") return id ? packSet(id) : null;
  if (kind === "mine") return mineSet(custom);
  if (kind === "play" && id) {
    const topic = rest.find((r) => r.startsWith("t-"))?.slice(2) ?? "all";
    const audience = rest.find((r) => isAudience(r)) ?? "everyone";
    return categorySet(id, audience as AudienceChoice, topic);
  }
  return null;
}
