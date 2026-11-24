import type { Question, TriviaTopic } from "../types";

// The ten trivia areas a player can choose from. The ids are saved in the browser and in saved rounds,
// so the older ones (geography, history, science, culture, logic) keep their names.
export interface TopicGroup {
  id: string;
  label: string;
  topics: readonly TriviaTopic[];
}

export const topicGroups: readonly TopicGroup[] = [
  { id: "geography", label: "Geography & places", topics: ["Geography"] },
  { id: "history", label: "History", topics: ["History"] },
  { id: "science", label: "Science & nature", topics: ["Science"] },
  { id: "screen", label: "Movies & TV", topics: ["Movies & TV"] },
  { id: "music", label: "Music & entertainment", topics: ["Music & entertainment"] },
  { id: "sports", label: "Sports & games", topics: ["Sports & games"] },
  { id: "food", label: "Food & drink", topics: ["Food & drink"] },
  { id: "culture", label: "Art, books & culture", topics: ["Art, books & culture"] },
  { id: "tech", label: "Technology & inventions", topics: ["Technology"] },
  { id: "logic", label: "General knowledge & logic", topics: ["General & logic"] },
];

export const topicGroupById = (id: string): TopicGroup | undefined => topicGroups.find((g) => g.id === id);

export const isTopicGroupId = (value: unknown): value is string => typeof value === "string" && (value === "all" || !!topicGroupById(value));

export function inTopicGroup(q: Question, groupId: string): boolean {
  if (groupId === "all") return true;
  const group = topicGroupById(groupId);
  return q.kind === "trivia" && !!group && group.topics.includes(q.topic);
}
