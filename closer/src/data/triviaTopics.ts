import type { Question, TriviaTopic } from "../types";

// The quiz has seven fine-grained topics, some with only a few questions. For the topic picker they
// are grouped so every choice has enough questions for a real round.
export interface TopicGroup {
  id: string;
  label: string;
  topics: readonly TriviaTopic[];
}

export const topicGroups: readonly TopicGroup[] = [
  { id: "geography", label: "Geography", topics: ["Geography"] },
  { id: "history", label: "History", topics: ["History"] },
  { id: "science", label: "Science", topics: ["Science"] },
  { id: "culture", label: "Entertainment & culture", topics: ["Entertainment", "Culture"] },
  { id: "logic", label: "Logic & general knowledge", topics: ["Logic", "General knowledge"] },
];

export const topicGroupById = (id: string): TopicGroup | undefined => topicGroups.find((g) => g.id === id);

export const isTopicGroupId = (value: unknown): value is string => typeof value === "string" && (value === "all" || !!topicGroupById(value));

export function inTopicGroup(q: Question, groupId: string): boolean {
  if (groupId === "all") return true;
  const group = topicGroupById(groupId);
  return q.kind === "trivia" && !!group && group.topics.includes(q.topic);
}
