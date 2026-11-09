import { describe, expect, it } from "vitest";
import { guessQuestions } from "./data/guessQuestions";
import type { Depth } from "./types";
import { dailyFor, localDateKey } from "./utils/daily";
import * as game from "./utils/guessGame";
import { parseRoute } from "./utils/router";
import {
  advance, changeLevel, progress, recordOutcome, remainingByLevel, restoreSession, startSession, summarize,
  type PoolItem, type SessionState,
} from "./utils/session";
import { shuffle } from "./utils/shuffle";
import {
  createFavoritesStore, loadAnswers, loadDailyAnswer, loadSession, saveAnswer, saveDailyAnswer, saveSession,
  type KeyValueStore,
} from "./utils/storage";

const list = [{ id: "a", text: "A?" }, { id: "b", text: "B?" }, { id: "c", text: "C?" }];

function memoryStore(): KeyValueStore {
  const data = new Map<string, string>();
  return { getItem: (k) => data.get(k) ?? null, setItem: (k, v) => void data.set(k, v) };
}

function seeded(seed = 1) {
  return () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
}

const blocked: KeyValueStore = {
  getItem: () => { throw new Error("blocked"); },
  setItem: () => { throw new Error("blocked"); },
};

describe("daily question", () => {
  it("uses the local calendar date", () => {
    expect(localDateKey(new Date(2026, 0, 5, 23, 59))).toBe("2026-01-05");
  });

  it("stays the same all day and changes the next day", () => {
    const morning = dailyFor(new Date(2026, 9, 25, 0, 1), list);
    const night = dailyFor(new Date(2026, 9, 25, 23, 59), list);
    const tomorrow = dailyFor(new Date(2026, 9, 26, 9, 0), list);
    expect(morning.question).toEqual(night.question);
    expect(tomorrow.question).not.toEqual(morning.question);
    expect(morning.dateKey).toBe("2026-10-25");
  });

  it("cycles through the whole list", () => {
    const seen = new Set<string>();
    for (let day = 1; day <= list.length; day++) seen.add(dailyFor(new Date(2026, 9, day), list).question.id);
    expect(seen.size).toBe(list.length);
  });
});

describe("Fisher-Yates shuffle", () => {
  const items = Array.from({ length: 20 }, (_, i) => i);

  it("keeps every item exactly once and leaves the input alone", () => {
    const copy = [...items];
    const out = shuffle(items, seeded());
    expect([...out].sort((a, b) => a - b)).toEqual(items);
    expect(items).toEqual(copy);
  });

  it("is driven by the random source it is given", () => {
    expect(shuffle(items, seeded(7))).toEqual(shuffle(items, seeded(7)));
    expect(shuffle(items, seeded(7))).not.toEqual(items);
  });

  it("gives every item a fair chance at every position", () => {
    const counts = Array.from({ length: 4 }, () => Array<number>(4).fill(0));
    const random = seeded(3);
    for (let n = 0; n < 8000; n++) shuffle([0, 1, 2, 3], random).forEach((v, pos) => counts[v][pos]++);
    for (const row of counts) for (const c of row) expect(c).toBeGreaterThan(1700); // expected 2000
  });
});

// 12 questions: three at each depth level.
const pool: PoolItem[] = Array.from({ length: 12 }, (_, i) => ({ id: `q${i}`, depth: ((i % 4) + 1) as Depth }));
const depthOf = (id: string | null) => pool.find((q) => q.id === id)?.depth;

/** Skips through everything left, returning the ids in the order they were shown. */
function playAll(state: SessionState): { shown: string[]; end: SessionState } {
  const shown: string[] = [];
  let s = state;
  while (s.currentId) {
    shown.push(s.currentId);
    s = advance(s, pool);
  }
  return { shown, end: s };
}

describe("a play session", () => {
  it("shows every question once, in a shuffled order, then finishes", () => {
    const { shown, end } = playAll(startSession("love", pool, { random: seeded() }));
    expect(shown).toHaveLength(12);
    expect(new Set(shown).size).toBe(12);
    expect(shown).not.toEqual(pool.map((q) => q.id));
    expect(end.done).toBe(true);
  });

  it("counts a skipped question as seen and never asks it again", () => {
    let s = startSession("love", pool, { random: seeded() });
    const first = s.currentId!;
    s = advance(s, pool);
    expect(s.outcomes[first]).toBe("skipped");
    expect(s.seen).toContain(first);
    expect(playAll(s).shown).not.toContain(first);
  });

  it("finishes with a completion state and restarts with a fresh shuffle", () => {
    const { end } = playAll(startSession("love", pool, { random: seeded(1) }));
    expect(end.currentId).toBeNull();
    expect(progress(end, pool)).toEqual({ done: 12, total: 12 });
    const again = startSession("love", pool, { random: seeded(99) });
    expect(again.done).toBe(false);
    expect(again.seen).toHaveLength(1);
    expect(again.order).not.toEqual(end.order);
  });

  it("only asks questions of the chosen depth", () => {
    const { shown } = playAll(startSession("love", pool, { level: 3, random: seeded() }));
    expect(shown).toHaveLength(3);
    expect(shown.every((id) => depthOf(id) === 3)).toBe(true);
  });

  it("never repeats a question when depth changes mid-session", () => {
    let s = startSession("love", pool, { random: seeded(5) });
    const shown: string[] = [s.currentId!];
    for (const level of [2, 4, "mix", 1, 3, "mix", 2, 4, "mix"] as const) {
      s = changeLevel(s, pool, level);
      if (s.currentId && !shown.includes(s.currentId)) shown.push(s.currentId);
      s = advance(s, pool);
      if (s.currentId) shown.push(s.currentId);
    }
    expect(new Set(shown).size).toBe(shown.length);
    expect(new Set(s.seen).size).toBe(s.seen.length);
  });

  it("keeps the question on screen when it fits the new depth, and swaps it when it doesn't", () => {
    let s = startSession("love", pool, { level: 2, random: seeded() });
    const current = s.currentId!;
    expect(changeLevel(s, pool, "mix").currentId).toBe(current);
    s = changeLevel(s, pool, 4);
    expect(s.currentId).not.toBe(current);
    expect(s.outcomes[current]).toBe("skipped");
    expect(depthOf(s.currentId)).toBe(4);
  });

  it("reports completion when a depth has nothing left, and resumes at another depth", () => {
    let { end: s } = playAll(startSession("love", pool, { level: 1, random: seeded() }));
    expect(s.done).toBe(true);
    expect(remainingByLevel(s, pool)).toEqual({ 1: 0, 2: 3, 3: 3, 4: 3 });
    s = changeLevel(s, pool, 2);
    expect(s.done).toBe(false);
    expect(depthOf(s.currentId)).toBe(2);
  });

  it("reports progress against the chosen depth", () => {
    let s = startSession("love", pool, { random: seeded() });
    expect(progress(s, pool)).toEqual({ done: 1, total: 12 });
    s = advance(s, pool);
    expect(progress(s, pool)).toEqual({ done: 2, total: 12 });
    s = changeLevel(s, pool, 2);
    expect(progress(s, pool).total).toBe(3);
  });

  it("limits a quiz to its length", () => {
    const s = startSession("trivia", pool, { limit: 5, random: seeded() });
    expect(progress(s, pool)).toEqual({ done: 1, total: 5 });
    const { shown, end } = playAll(s);
    expect(shown).toHaveLength(5);
    expect(end.done).toBe(true);
  });

  it("scores a question only once", () => {
    let s = startSession("trivia", pool, { limit: 5, random: seeded() });
    const first = s.currentId!;
    s = recordOutcome(s, "correct");
    s = recordOutcome(s, "incorrect");
    s = recordOutcome(s, "skipped");
    expect(summarize(s)).toMatchObject({ answered: 1, correct: 1, incorrect: 0, skipped: 0, percent: 100 });
    s = advance(s, pool);
    expect(s.outcomes[first]).toBe("correct");
  });

  it("summarizes answered, correct, incorrect, skipped and percentage", () => {
    let s = startSession("trivia", pool, { limit: 4, random: seeded() });
    s = advance(recordOutcome(s, "correct"), pool);
    s = advance(recordOutcome(s, "incorrect"), pool);
    s = advance(recordOutcome(s, "correct"), pool);
    s = advance(s, pool); // skipped
    expect(summarize(s)).toEqual({ answered: 3, skipped: 1, correct: 2, incorrect: 1, percent: 67 });
    expect(s.done).toBe(true);
  });

  it("restores a saved session only when it still matches the pool", () => {
    const store = memoryStore();
    const s = advance(startSession("love", pool, { random: seeded() }), pool);
    saveSession("play:love", s, store);
    const saved = loadSession("play:love", store);
    expect(restoreSession(saved, "love", pool, null)).toEqual(s);
    expect(restoreSession(saved, "party", pool, null)).toBeNull();
    expect(restoreSession(saved, "love", pool.slice(1), null)).toBeNull();
    expect(restoreSession(saved, "love", pool, 10)).toBeNull();
    expect(restoreSession({ junk: true }, "love", pool, null)).toBeNull();
    expect(restoreSession(null, "love", pool, null)).toBeNull();
  });
});

describe("favorites", () => {
  it("toggles, never duplicates, and remembers across visits", () => {
    const store = memoryStore();
    const first = createFavoritesStore(store);
    expect(first.toggle("love-1")).toBe(true);
    expect(first.toggle("deep-2")).toBe(true);
    expect(first.get()).toEqual(["love-1", "deep-2"]);
    expect(first.toggle("love-1")).toBe(false);
    expect(first.has("love-1")).toBe(false);
    expect(createFavoritesStore(store).get()).toEqual(["deep-2"]);
  });

  it("ignores duplicates and junk in what was saved", () => {
    const store = memoryStore();
    store.setItem("closer.favorites", JSON.stringify(["a", "a", 3, null, "b"]));
    expect(createFavoritesStore(store).get()).toEqual(["a", "b"]);
    store.setItem("closer.favorites", "not json");
    expect(createFavoritesStore(store).get()).toEqual([]);
  });

  it("notifies listeners and stops once unsubscribed", () => {
    const favs = createFavoritesStore(memoryStore());
    let calls = 0;
    const off = favs.subscribe(() => calls++);
    favs.toggle("x");
    off();
    favs.toggle("y");
    expect(calls).toBe(1);
  });

  it("keeps working in memory when the browser blocks storage", () => {
    const favs = createFavoritesStore(blocked);
    expect(favs.toggle("love-1")).toBe(true);
    expect(favs.has("love-1")).toBe(true);
    const none = createFavoritesStore(null);
    expect(none.toggle("a")).toBe(true);
    expect(none.get()).toEqual(["a"]);
  });
});

describe("Guess My Answer", () => {
  const themed = guessQuestions.filter((q) => q.themeId === "party");
  const start = () => game.startGame(["Ana", "Ben"], themed, 4, seeded(2));
  /** One whole round: the answerer locks `secret`, the guesser submits `guess`. */
  const round = (s: game.GuessState, secret: number, guess: number) =>
    game.submitGuess(game.beginGuessing(game.lockAnswer(game.beginAnswering(s), secret)), guess);

  it("picks the requested number of different questions", () => {
    const s = start();
    expect(s.questions).toHaveLength(4);
    expect(new Set(s.questions.map((q) => q.id)).size).toBe(4);
    expect(s.phase).toBe("handoff-answer");
  });

  it("walks through the phases in order and keeps the secret until the reveal", () => {
    let s = game.lockAnswer(start(), 1); // too early: nobody is answering yet
    expect(s.secret).toBeNull();
    s = game.lockAnswer(game.beginAnswering(s), 1);
    expect(s.phase).toBe("handoff-guess");
    s = game.submitGuess(s, 1); // can't guess before the guesser takes the device
    expect(s.guess).toBeNull();
    s = game.submitGuess(game.beginGuessing(s), 1);
    expect(s.phase).toBe("reveal");
    expect(s.secret).toBe(1);
  });

  it("scores the guesser only when the guess matches, and only once", () => {
    let s = round(start(), 2, 2);
    expect(s.scores).toEqual([0, 1]); // round 0: Ana answers, Ben guesses
    s = game.submitGuess(game.submitGuess(s, 2), 2);
    expect(s.scores).toEqual([0, 1]);
  });

  it("gives no point for a wrong guess", () => {
    expect(round(start(), 0, 3).scores).toEqual([0, 0]);
  });

  it("alternates roles every round", () => {
    expect([0, 1, 2, 3].map(game.answererOf)).toEqual([0, 1, 0, 1]);
    expect([0, 1, 2, 3].map(game.guesserOf)).toEqual([1, 0, 1, 0]);
    let s = game.nextRound(round(start(), 1, 1));
    expect(s.round).toBe(1);
    s = round(s, 0, 0);
    expect(s.scores).toEqual([1, 1]); // round 1: Ben answers, Ana guesses
  });

  it("ends with the final score, names the winner, and replays from zero", () => {
    let s = start();
    for (let r = 0; r < 4; r++) s = game.nextRound(round(s, 0, r < 3 ? 0 : 1));
    expect(s.phase).toBe("final");
    expect(s.scores).toEqual([1, 2]); // Ben guesses rounds 1 and 3, Ana rounds 2 and 4; the last guess missed
    expect(game.winner(s)).toBe(1);
    const again = game.replay(s, themed, seeded(8));
    expect(again.scores).toEqual([0, 0]);
    expect(again.phase).toBe("handoff-answer");
    expect(again.questions).toHaveLength(4);
    expect(game.winner({ ...s, scores: [2, 2] })).toBe("tie");
  });

  it("ignores impossible option numbers", () => {
    let s = game.beginAnswering(start());
    expect(game.lockAnswer(s, 4).phase).toBe("answering");
    expect(game.lockAnswer(s, -1).phase).toBe("answering");
    s = game.beginGuessing(game.lockAnswer(s, 0));
    expect(game.submitGuess(s, 9).phase).toBe("guessing");
  });
});

describe("saved answers", () => {
  it("keeps question answers and the day's answer", () => {
    const store = memoryStore();
    saveAnswer("love-1", "Walks by the lake", store);
    expect(loadAnswers(store)["love-1"].text).toBe("Walks by the lake");
    saveDailyAnswer("2026-10-25", "daily-3", "My sister", store);
    expect(loadDailyAnswer("2026-10-25", store)).toEqual({ questionId: "daily-3", text: "My sister" });
    expect(loadDailyAnswer("2026-10-26", store)).toBeNull();
  });

  it("never breaks the page when the browser blocks storage", () => {
    expect(() => saveAnswer("x", "y", blocked)).not.toThrow();
    expect(loadAnswers(blocked)).toEqual({});
    expect(loadDailyAnswer("2026-10-25", blocked)).toBeNull();
  });
});

describe("page addresses", () => {
  it("map to pages", () => {
    expect(parseRoute("")).toEqual({ page: "home" });
    expect(parseRoute("#/")).toEqual({ page: "home" });
    expect(parseRoute("#/explore")).toEqual({ page: "explore" });
    expect(parseRoute("#/about/")).toEqual({ page: "about" });
    expect(parseRoute("#/play/would-you-rather")).toEqual({ page: "play", categoryId: "would-you-rather" });
    expect(parseRoute("#/favorites")).toEqual({ page: "favorites" });
    expect(parseRoute("#/favorites/play")).toEqual({ page: "favorites-play", categoryId: null });
    expect(parseRoute("#/favorites/play/love")).toEqual({ page: "favorites-play", categoryId: "love" });
    expect(parseRoute("#/guess")).toEqual({ page: "guess" });
    expect(parseRoute("#/nowhere")).toEqual({ page: "not-found" });
  });
});
