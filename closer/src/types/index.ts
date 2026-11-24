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

/** The pastel background colors a category card can take (defined in index.css). */
export type CategoryTint = "rose" | "lavender" | "yellow" | "peach" | "mint" | "sky";

export interface Category {
  id: CategoryId;
  name: string;
  /** One line for the category card. */
  description: string;
  icon: IconName;
  /** Tailwind gradient classes for the icon tile, e.g. "from-plum-500 to-coral-400". */
  gradient: string;
  /** The pastel color of the category's card on Home and Explore. */
  tint: CategoryTint;
  /** The library groups whose questions this experience plays (always including its own id). */
  sources: CategoryId[];
}

/**
 * How deep a question goes. Conversation categories: 1 Fun & Light, 2 Meaningful, 3 Deep, 4 Bold.
 * Trivia uses the same four steps as difficulty: 1 Easy, 2 Medium, 3 Hard, 4 Expert.
 */
export type Depth = 1 | 2 | 3 | 4;

/** A question as written in the library files: its depth, then its words. The id comes from its place in the list. */
export type OpenEntry = readonly [Depth, string];

export type TriviaTopic =
  | "Geography" | "History" | "Science" | "Movies & TV" | "Music & entertainment" | "Sports & games"
  | "Food & drink" | "Art, books & culture" | "Technology" | "General & logic";

export interface TriviaEntry {
  topic: TriviaTopic;
  /** The Wikipedia article the fact was checked against. */
  source: string;
  difficulty: Depth;
  text: string;
  options: readonly [string, string, string, string];
  /** Index of the correct option. */
  answer: 0 | 1 | 2 | 3;
  explanation: string;
}

/** Who a question suits: the group playing decides which questions feel right. */
export type Audience = "couple" | "friends" | "family" | "team";

/** What the person picked on the Explore page: a group, or "everyone" for no filter. */
export type AudienceChoice = Audience | "everyone";

/** Where an open question comes from: one of the library's categories, a seasonal pack, or the player's own. */
export type OpenSource = Exclude<CategoryId, "trivia"> | "pack" | "mine";

/** What a Would You Rather or debate prompt is about (see data/choices/bank.ts). */
export type ChoiceTopicId = "funny" | "food" | "travel" | "bonds" | "money" | "pop" | "future" | "ethics" | "society" | "powers";

export interface OpenQuestion {
  id: string;
  categoryId: OpenSource;
  kind: "open";
  depth: Depth;
  /** Only Would You Rather and debate prompts have one. */
  topic?: ChoiceTopicId;
  text: string;
}

export interface TriviaQuestion {
  id: string;
  categoryId: "trivia";
  kind: "trivia";
  /** The difficulty: 1 Easy to 4 Expert. */
  depth: Depth;
  topic: TriviaTopic;
  source: string;
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

export type GuessThemeId =
  | "love" | "party" | "would-you-rather" | "family" | "icebreakers" | "imagination"
  | "travel" | "food" | "nostalgia" | "everyday";

/** Names of the Lucide icons the seasonal packs use (see components/PackIcon). */
export type PackIconName = "Heart" | "Sparkles" | "Sun" | "Ghost" | "Leaf" | "Snowflake" | "Cake";

/** A set of questions for one occasion. `season` is the stretch of the year it is "in season"; leave it out for an any-day pack. */
export interface Pack {
  id: string;
  name: string;
  blurb: string;
  icon: PackIconName;
  gradient: string;
  /** Inclusive month/day range; it may run over New Year (Dec 26 to Jan 15). */
  season?: { from: readonly [month: number, day: number]; to: readonly [month: number, day: number] };
  entries: readonly OpenEntry[];
}

/** A question for Guess My Answer: four answers to pick from, so a guess can be marked right or wrong without grading free text. */
export interface GuessQuestion {
  id: string;
  themeId: GuessThemeId;
  text: string;
  options: readonly [string, string, string, string];
}
