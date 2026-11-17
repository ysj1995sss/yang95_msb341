import {
  Bomb, Camera, CircleHelp, Dices, Drama, Flame, Hand, History, Lightbulb, Link2, Megaphone,
  Quote, Swords, Timer, UserCheck, Vote, type LucideIcon,
} from "lucide-react";
import type { CategoryTint } from "../types";

export type GameGroupId = "party" | "know" | "two" | "make" | "brain";

export interface GameInfo {
  id: string;
  title: string;
  /** One line for the game's page header. */
  blurb: string;
  /** The hub card's text: how it plays. */
  text: string;
  /** "2 to 8 players". */
  players: string;
  group: GameGroupId;
  icon: LucideIcon;
  gradient: string;
  tint: CategoryTint;
}

export const gameGroups: readonly { id: GameGroupId; title: string; text: string }[] = [
  { id: "party", title: "Party starters", text: "Loud, quick and good for a room full of people." },
  { id: "know", title: "Know each other", text: "Find out what you really know about one another." },
  { id: "two", title: "For two", text: "Made for a couple, or any pair who likes a good evening in." },
  { id: "make", title: "Make something up", text: "Stories, jokes and silly inventions, written together." },
  { id: "brain", title: "Brain games", text: "Facts, numbers and races to the right answer." },
];

export const games: readonly GameInfo[] = [
  {
    id: "truth-or-dare", title: "Truth or Dare", players: "2 to 8 players", group: "party", icon: Flame, tint: "rose", gradient: "from-coral-500 to-plum-500",
    blurb: "Truth gets a real question. Dare gets a short, silly task.",
    text: "On your turn, tap Truth for a question from the library or Dare for a quick silly task. You choose how bold it gets.",
  },
  {
    id: "never-have-i-ever", title: "Never Have I Ever", players: "2 to 8 players", group: "party", icon: Hand, tint: "peach", gradient: "from-amber-400 to-coral-500",
    blurb: "Tap everyone who has done it. Three lives each.",
    text: "A statement appears. Everyone who has done it loses a finger on the phone. Last one with fingers up wins.",
  },
  {
    id: "pass-the-bomb", title: "Pass the Bomb", players: "2 to 8 players", group: "party", icon: Bomb, tint: "yellow", gradient: "from-plum-600 to-coral-500",
    blurb: "A hidden fuse is burning. Pass it fast.",
    text: "A fuse of unknown length runs while the phone goes round. Whoever holds it at the bang answers a question and loses a life.",
  },
  {
    id: "most-likely-to", title: "Most Likely To", players: "3 to 10 players", group: "party", icon: Vote, tint: "lavender", gradient: "from-plum-500 to-sky-400",
    blurb: "Everyone points at once. Count the fingers.",
    text: "A \"who is most likely to…\" prompt appears, everyone points at the same moment, and the phone keeps the tally.",
  },
  {
    id: "last-word", title: "Last Word", players: "2 to 8 players", group: "party", icon: Timer, tint: "mint", gradient: "from-emerald-500 to-sky-400",
    blurb: "One related word each, no repeats, no pauses.",
    text: "A topic appears and players take turns saying one related word. Hesitate for five seconds, or repeat one, and you are out.",
  },
  {
    id: "rapid-fire", title: "Rapid Fire", players: "1 to 6 players", group: "party", icon: Megaphone, tint: "sky", gradient: "from-sky-400 to-plum-600",
    blurb: "Ten questions in sixty seconds, one-word answers only.",
    text: "Each player gets a minute. Tap Right for every quick one-word answer, Skip for the ones you can't.",
  },
  {
    id: "how-well-do-you-know-me", title: "How Well Do You Know Me?", players: "2 to 6 players", group: "know", icon: UserCheck, tint: "lavender", gradient: "from-plum-600 to-coral-500",
    blurb: "One person answers in secret. The rest guess.",
    text: "In the hot seat you answer five this-or-that questions privately. Then everyone else guesses your answers together.",
  },
  {
    id: "two-truths-and-a-lie", title: "Two Truths and a Lie", players: "3 to 8 players", group: "know", icon: Drama, tint: "peach", gradient: "from-coral-500 to-plum-600",
    blurb: "Three statements about you. Which one is the lie?",
    text: "You type three statements in private and mark the lie. The group sees them shuffled and votes. Fool them and you score.",
  },
  {
    id: "match-game", title: "Match Game", players: "2 players", group: "know", icon: Link2, tint: "mint", gradient: "from-emerald-500 to-plum-500",
    blurb: "Answer separately. See how often you match.",
    text: "Two players answer the same questions in secret. Reveal each match as you go, or answer a dozen and get one compatibility percentage at the end.",
  },
  {
    id: "memory-lane", title: "Memory Lane", players: "2 players", group: "two", icon: History, tint: "yellow", gradient: "from-amber-400 to-coral-500",
    blurb: "Remember-when prompts for the two of you.",
    text: "A \"remember when\" prompt for each of you, taking turns to tell it first. A good way to remember what you liked about each other.",
  },
  {
    id: "date-night-roulette", title: "Date Night Roulette", players: "2 players", group: "two", icon: Dices, tint: "lavender", gradient: "from-plum-500 to-coral-500",
    blurb: "Spin for a date idea that fits tonight.",
    text: "Pick a budget and a mood, spin, and the phone lands on a date idea. Spin again until it feels right.",
  },
  {
    id: "story-chain", title: "Story Chain", players: "2 to 8 players", group: "make", icon: Quote, tint: "sky", gradient: "from-sky-400 to-plum-500",
    blurb: "One sentence each, until you have a story.",
    text: "The phone gives you the first line. Each player adds a sentence (or one word, if you want it harder), and at the end the story is read out.",
  },
  {
    id: "caption-this", title: "Caption This", players: "3 to 8 players", group: "make", icon: Camera, tint: "yellow", gradient: "from-amber-400 to-plum-500",
    blurb: "A scene appears. Write the funniest caption.",
    text: "Everyone writes a caption in secret, the phone shows them mixed up, and the group picks the funniest one.",
  },
  {
    id: "invent-a-product", title: "Invent a Product", players: "2 to 8 players", group: "make", icon: Lightbulb, tint: "mint", gradient: "from-emerald-500 to-sky-400",
    blurb: "A problem, a twist, and one minute to pitch.",
    text: "A random problem comes up, maybe with a twist your invention must include. Each player pitches for a minute and the room votes.",
  },
  {
    id: "brain-quiz", title: "Brain Quiz", players: "1 to 6 players", group: "brain", icon: CircleHelp, tint: "lavender", gradient: "from-plum-500 to-sky-400",
    blurb: "Fact or fiction, higher or lower, and guess the price.",
    text: "Take turns with one question each: is this fact true, is the next number higher or lower, or which price is closest. Play one kind, or mix all three.",
  },
  {
    id: "trivia-duel", title: "Trivia Duel", players: "2 players, face to face", group: "brain", icon: Swords, tint: "peach", gradient: "from-plum-600 to-coral-500",
    blurb: "Two players, one phone, first right answer wins.",
    text: "Lay the phone flat between you. Each player has their own four buttons. Tap first and be right. Tap wrong and the point goes to the other.",
  },
];

export const gameById = (id: string): GameInfo | undefined => games.find((g) => g.id === id);
