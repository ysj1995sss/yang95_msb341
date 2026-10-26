export type CategoryId =
  | "love"
  | "deep"
  | "party"
  | "debate"
  | "family"
  | "icebreakers"
  | "would-you-rather"
  | "trivia"
  | "imagination"
  | "storytelling";

/** Names of the Lucide icons the categories use (see components/CategoryIcon). */
export type IconName =
  | "Heart" | "Waves" | "PartyPopper" | "Scale" | "Camera"
  | "Snowflake" | "Split" | "Brain" | "Sparkles" | "BookOpen";

export interface Category {
  id: CategoryId;
  name: string;
  /** One line for the category card. */
  description: string;
  icon: IconName;
  /** Tailwind gradient classes for the icon tile, e.g. "from-plum-500 to-coral-400". */
  gradient: string;
}

export interface OpenQuestion {
  id: string;
  categoryId: Exclude<CategoryId, "trivia">;
  kind: "open";
  text: string;
}

export interface TriviaQuestion {
  id: string;
  categoryId: "trivia";
  kind: "trivia";
  topic: "Geography" | "History" | "Science" | "Movies" | "General knowledge";
  text: string;
  options: [string, string, string, string];
  /** Index of the correct option. */
  answer: 0 | 1 | 2 | 3;
  explanation: string;
}

export type Question = OpenQuestion | TriviaQuestion;

export interface DailyQuestion {
  id: string;
  text: string;
}
