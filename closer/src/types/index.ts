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

/**
 * How deep a question goes. Conversation categories: 1 Fun & Light, 2 Meaningful, 3 Deep, 4 Bold.
 * Trivia uses the same four steps as difficulty: 1 Easy, 2 Medium, 3 Hard, 4 Expert.
 */
export type Depth = 1 | 2 | 3 | 4;

/** A question as written in the library files: its depth, then its words. The id comes from its place in the list. */
export type OpenEntry = readonly [Depth, string];

export type TriviaTopic =
  | "Geography" | "History" | "Science" | "Entertainment" | "Culture" | "Logic" | "General knowledge";

export interface TriviaEntry {
  topic: TriviaTopic;
  difficulty: Depth;
  text: string;
  options: readonly [string, string, string, string];
  /** Index of the correct option. */
  answer: 0 | 1 | 2 | 3;
  explanation: string;
}

export interface OpenQuestion {
  id: string;
  categoryId: Exclude<CategoryId, "trivia">;
  kind: "open";
  depth: Depth;
  text: string;
}

export interface TriviaQuestion {
  id: string;
  categoryId: "trivia";
  kind: "trivia";
  /** The difficulty: 1 Easy to 4 Expert. */
  depth: Depth;
  topic: TriviaTopic;
  text: string;
  options: readonly [string, string, string, string];
  answer: 0 | 1 | 2 | 3;
  explanation: string;
}

export type Question = OpenQuestion | TriviaQuestion;

export interface DailyQuestion {
  id: string;
  text: string;
}

export type GuessThemeId = "love" | "party" | "would-you-rather" | "family" | "icebreakers" | "imagination";

/** A question for Guess My Answer: four answers to pick from, so a guess can be marked right or wrong without grading free text. */
export interface GuessQuestion {
  id: string;
  themeId: GuessThemeId;
  text: string;
  options: readonly [string, string, string, string];
}
