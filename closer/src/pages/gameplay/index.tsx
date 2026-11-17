import { lazy, type ComponentType } from "react";

/** Each game's screen, by the id used in its address (#/games/truth-or-dare) and in data/games.ts.
 *  The screens load when a game is opened, in five groups, so the first visit stays small; the
 *  service worker keeps every group, so they still open offline. */
const party = (name: "TruthOrDare" | "NeverHaveIEver" | "PassTheBomb" | "MostLikelyTo" | "LastWord" | "RapidFire") =>
  lazy(() => import("./party").then((m) => ({ default: m[name] })));
const know = (name: "HowWellDoYouKnowMe" | "TwoTruthsAndALie" | "MatchGame" | "MemoryLane") =>
  lazy(() => import("./know").then((m) => ({ default: m[name] })));
const make = (name: "StoryChain" | "CaptionThis" | "InventAProduct") =>
  lazy(() => import("./make").then((m) => ({ default: m[name] })));
const brain = (name: "TriviaDuel" | "BrainQuiz") =>
  lazy(() => import("./brain").then((m) => ({ default: m[name] })));
const dates = lazy(() => import("./dates").then((m) => ({ default: m.DateNightRoulette })));

export const gameScreens: Record<string, ComponentType> = {
  "truth-or-dare": party("TruthOrDare"),
  "never-have-i-ever": party("NeverHaveIEver"),
  "pass-the-bomb": party("PassTheBomb"),
  "most-likely-to": party("MostLikelyTo"),
  "last-word": party("LastWord"),
  "rapid-fire": party("RapidFire"),
  "how-well-do-you-know-me": know("HowWellDoYouKnowMe"),
  "two-truths-and-a-lie": know("TwoTruthsAndALie"),
  "match-game": know("MatchGame"),
  "memory-lane": know("MemoryLane"),
  "date-night-roulette": dates,
  "story-chain": make("StoryChain"),
  "caption-this": make("CaptionThis"),
  "invent-a-product": make("InventAProduct"),
  "trivia-duel": brain("TriviaDuel"),
  "brain-quiz": brain("BrainQuiz"),
};
