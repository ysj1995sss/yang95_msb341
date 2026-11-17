import type { Category, CategoryId } from "../types";

/** The experiences people pick from: seven of them. Some hold more than one library group (see `sources`),
 *  because the questions overlapped. The merged ones keep one of the old ids, so saved links still work. */
export const categories: Category[] = [
  {
    id: "love",
    name: "Love & Relationships",
    description: "Romance, dating, intimacy and the little things that bring you closer.",
    icon: "Heart",
    gradient: "from-coral-500 to-plum-500",
    tint: "rose",
    sources: ["love"],
  },
  {
    id: "deep",
    name: "Deep Connections",
    description: "Values, feelings and growth: the conversations that stay with you.",
    icon: "Waves",
    gradient: "from-plum-600 to-plum-400",
    tint: "lavender",
    sources: ["deep"],
  },
  {
    id: "party",
    name: "Icebreakers & Party Games",
    description: "Easy openers, funny questions and truth or dare, for new friends, teams and a loud room.",
    icon: "PartyPopper",
    gradient: "from-coral-400 to-amber-400",
    tint: "yellow",
    sources: ["party", "icebreakers"],
  },
  {
    id: "would-you-rather",
    name: "Would You Rather & Debates",
    description: "Dilemmas, trade-offs and hot takes. Pick a side and defend it.",
    icon: "Split",
    gradient: "from-coral-500 to-amber-400",
    tint: "peach",
    sources: ["would-you-rather", "debate"],
  },
  {
    id: "family",
    name: "Family & Memories",
    description: "Childhood, traditions and the stories worth passing down.",
    icon: "Camera",
    gradient: "from-amber-400 to-coral-500",
    tint: "mint",
    sources: ["family"],
  },
  {
    id: "imagination",
    name: "Imagination & Storytelling",
    description: "Invent, dream and design worlds that don't exist yet, then tell the stories behind your own.",
    icon: "Sparkles",
    gradient: "from-plum-400 to-coral-400",
    tint: "sky",
    sources: ["imagination", "storytelling"],
  },
  {
    id: "trivia",
    name: "Trivia & Brain Battles",
    description: "Multiple-choice quizzes on geography, history, science, entertainment and logic.",
    icon: "Brain",
    gradient: "from-plum-700 to-sky-400",
    tint: "yellow",
    sources: ["trivia"],
  },
];

/** The original ten groups the questions are written in. A question's id and its audience tags come from these. */
export const libraryNames: Record<CategoryId, string> = {
  love: "Love & Relationships",
  deep: "Deep Connections",
  party: "Party & Games",
  debate: "Debate & Opinions",
  family: "Family & Memories",
  icebreakers: "Icebreakers & Team Building",
  "would-you-rather": "Would You Rather & Dilemmas",
  imagination: "Imagination & Creativity",
  storytelling: "Storytelling Challenges",
  trivia: "Trivia & Brain Battles",
};
export const libraryIds = Object.keys(libraryNames) as CategoryId[];

/** Addresses from before the merge (#/play/storytelling) lead to the experience that absorbed them. */
const merged: Record<string, string> = { storytelling: "imagination", debate: "would-you-rather", icebreakers: "party" };

export const categoryById = (id: string): Category | undefined => {
  const canonical = merged[id] ?? id;
  return categories.find((c) => c.id === canonical);
};

/** The experience a question lives in, from the library group it was written in. */
export const categoryOf = (libraryId: string): Category | undefined => categories.find((c) => (c.sources as string[]).includes(libraryId));
