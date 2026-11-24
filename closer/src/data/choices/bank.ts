import type { ChoiceTopicId, Depth, OpenQuestion } from "../../types";
import { bonds } from "./bonds";
import { ethics } from "./ethics";
import { food } from "./food";
import { funny } from "./funny";
import { future } from "./future";
import { money } from "./money";
import { pop } from "./pop";
import { powers } from "./powers";
import { society } from "./society";
import { travel } from "./travel";

// Would You Rather and debate prompts, one file per topic, one prompt per line:
//   W2 be early or be late      -> "Would you rather be early or be late?", intensity 2 (Meaningful)
//   W2 A whole sentence?        -> used as written (it ends in "?" or ".")
//   D3 Some claim.              -> a debate, intensity 3 (Deep)
// Ids are the format, topic and place ("debate-food-12"), so add lines at the END of their group;
// never insert, reorder or delete one, or saved favorites would point at another prompt.

export const choiceTopics: readonly { id: ChoiceTopicId; label: string }[] = [
  { id: "funny", label: "Funny & absurd" },
  { id: "food", label: "Food & everyday life" },
  { id: "travel", label: "Travel & adventure" },
  { id: "bonds", label: "Relationships & friendship" },
  { id: "money", label: "Work, money & success" },
  { id: "pop", label: "Movies, music & pop culture" },
  { id: "future", label: "Technology & the future" },
  { id: "ethics", label: "Ethics & big decisions" },
  { id: "society", label: "Society & community" },
  { id: "powers", label: "Imagination & superpowers" },
];

const files: Record<ChoiceTopicId, string> = { funny, food, travel, bonds, money, pop, future, ethics, society, powers };

export const choiceBank: OpenQuestion[] = choiceTopics.flatMap(({ id: topic }) => {
  const count = { W: 0, D: 0 };
  return files[topic].trim().split("\n").map((line): OpenQuestion => {
    const format = line[0] as "W" | "D";
    const body = line.slice(3);
    const categoryId = format === "W" ? "would-you-rather" : "debate";
    count[format]++;
    return {
      id: `${categoryId}-${topic}-${count[format]}`, categoryId, kind: "open", depth: Number(line[1]) as Depth, topic,
      text: /[?.]$/.test(body) ? body : `Would you rather ${body}?`,
    };
  });
});

// The 100 prompts written before the bank keep their ids; these are their topics, in order.
const words = (s: string) => s.trim().split(/\s+/) as ChoiceTopicId[];
const earlier: Record<string, ChoiceTopicId[]> = {
  "would-you-rather": words(`powers money ethics travel powers future travel powers ethics pop bonds bonds powers food funny pop powers
    powers money food future bonds ethics food ethics money bonds money ethics bonds ethics bonds bonds ethics ethics bonds money powers
    ethics bonds bonds bonds bonds society money ethics ethics bonds society ethics`),
  debate: words(`bonds money bonds future bonds money food bonds future ethics money food food food bonds funny pop money future money money
    money society money society society future bonds society bonds future ethics ethics future future bonds money society ethics bonds
    bonds future ethics ethics ethics bonds bonds society society society`),
};

/** The topic of the nth question (from 0) of an original group, when that group has topics. */
export const earlierTopic = (categoryId: string, n: number): ChoiceTopicId | undefined => earlier[categoryId]?.[n];
