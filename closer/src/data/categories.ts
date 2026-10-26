import type { Category } from "../types";

export const categories: Category[] = [
  {
    id: "love",
    name: "Love & Relationships",
    description: "Romance, dating, intimacy and the little things that bring you closer.",
    icon: "Heart",
    gradient: "from-coral-500 to-plum-500",
  },
  {
    id: "deep",
    name: "Deep Connections",
    description: "Values, feelings and growth: the conversations that stay with you.",
    icon: "Waves",
    gradient: "from-plum-600 to-plum-400",
  },
  {
    id: "party",
    name: "Party & Games",
    description: "Funny questions, truth or dare, and challenges for a loud room.",
    icon: "PartyPopper",
    gradient: "from-coral-400 to-amber-400",
  },
  {
    id: "debate",
    name: "Debate & Opinions",
    description: "Hot takes and friendly arguments. Pick a side and defend it.",
    icon: "Scale",
    gradient: "from-plum-500 to-coral-400",
  },
  {
    id: "family",
    name: "Family & Memories",
    description: "Childhood, traditions and the stories worth passing down.",
    icon: "Camera",
    gradient: "from-amber-400 to-coral-500",
  },
  {
    id: "icebreakers",
    name: "Icebreakers & Team Building",
    description: "Easy openers for new friends, new teams and first meetings.",
    icon: "Snowflake",
    gradient: "from-sky-400 to-plum-500",
  },
  {
    id: "would-you-rather",
    name: "Would You Rather",
    description: "Dilemmas and trade-offs. There's no right answer, only your answer.",
    icon: "Split",
    gradient: "from-coral-500 to-amber-400",
  },
  {
    id: "trivia",
    name: "Trivia & Brain Battles",
    description: "Multiple-choice questions on geography, history, science and film.",
    icon: "Brain",
    gradient: "from-plum-700 to-sky-400",
  },
  {
    id: "imagination",
    name: "Imagination & Creativity",
    description: "Invent, dream and design worlds that don't exist yet.",
    icon: "Sparkles",
    gradient: "from-plum-400 to-coral-400",
  },
  {
    id: "storytelling",
    name: "Storytelling Challenges",
    description: "Adventures, mishaps and life lessons, told your way.",
    icon: "BookOpen",
    gradient: "from-coral-400 to-plum-600",
  },
];

export const categoryById = (id: string): Category | undefined => categories.find((c) => c.id === id);
