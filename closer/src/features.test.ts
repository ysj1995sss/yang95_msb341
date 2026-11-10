import { describe, expect, it } from "vitest";
import { audiencesOf, audiencesOfEntry, matchesAudience } from "./data/audience";
import { debateMotions } from "./data/debateMotions";
import { categoryKey, categorySet, mineSet, packSet, setFromKey, surpriseSet } from "./data/playSets";
import { inSeason, orderedPacks, packQuestions, packs, seasonLabel } from "./data/packs";
import { questions } from "./data/questions";
import { inTopicGroup, topicGroups } from "./data/triviaTopics";
import * as debate from "./utils/debateGame";
import { createCustomStore, toOpenQuestion } from "./utils/custom";
import { shortcutFor, swipeOf } from "./utils/gestures";
import { installMode } from "./utils/install";
import { loadLastPlayed, roundProgress, saveLastPlayed } from "./utils/resume";
import { startSession, advance } from "./utils/session";
import { createSetting } from "./utils/settings";
import { saveSession, type KeyValueStore } from "./utils/storage";
import { resolveTheme } from "./utils/theme";
import { formatClock, secondsLeft, timerLabel } from "./utils/timer";

function memoryStore(): KeyValueStore {
  const data = new Map<string, string>();
  return { getItem: (k) => data.get(k) ?? null, setItem: (k, v) => void data.set(k, v) };
}
const blocked: KeyValueStore = {
  getItem: () => { throw new Error("blocked"); },
  setItem: () => { throw new Error("blocked"); },
};
function seeded(seed = 1) {
  return () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
}
const isString = (v: unknown): v is string => typeof v === "string";

describe("settings", () => {
  it("remembers a value across visits and tells subscribers", () => {
    const store = memoryStore();
    const a = createSetting("closer.test", "x", isString, store);
    let heard = 0;
    a.subscribe(() => heard++);
    a.set("y");
    expect(a.get()).toBe("y");
    expect(heard).toBe(1);
    expect(createSetting("closer.test", "x", isString, store).get()).toBe("y");
  });

  it("ignores a stored value that is the wrong kind, and works when storage is blocked", () => {
    const store = memoryStore();
    store.setItem("closer.test", JSON.stringify(42));
    expect(createSetting("closer.test", "x", isString, store).get()).toBe("x");
    const mem = createSetting("closer.test", "x", isString, blocked);
    mem.set("z");
    expect(mem.get()).toBe("z");
  });
});

describe("theme", () => {
  it("follows the device unless the person chose", () => {
    expect(resolveTheme("system", true)).toBe("dark");
    expect(resolveTheme("system", false)).toBe("light");
    expect(resolveTheme("light", true)).toBe("light");
    expect(resolveTheme("dark", false)).toBe("dark");
  });
});

describe("install button", () => {
  const env = { standalone: false, hasPrompt: false, maxTouchPoints: 0, platform: "Win32" };
  it("offers the install prompt where the browser allows it", () => {
    expect(installMode({ ...env, hasPrompt: true, userAgent: "Mozilla/5.0 (Windows NT 10.0) Chrome/120" })).toBe("prompt");
    expect(installMode({ ...env, hasPrompt: true, userAgent: "Mozilla/5.0 (Linux; Android 14) Chrome/120" })).toBe("prompt");
  });
  it("shows a hint on iPhone and iPad, where there is no prompt", () => {
    expect(installMode({ ...env, userAgent: "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) Safari/604" })).toBe("ios");
    expect(installMode({ ...env, userAgent: "Mozilla/5.0 (Macintosh; Intel Mac OS X) Safari/605", platform: "MacIntel", maxTouchPoints: 5 })).toBe("ios");
  });
  it("shows a menu hint on Android before the prompt arrives, and nothing on a desktop that can't install", () => {
    expect(installMode({ ...env, userAgent: "Mozilla/5.0 (Linux; Android 14) Chrome/120" })).toBe("android");
    expect(installMode({ ...env, userAgent: "Mozilla/5.0 (X11; Linux x86_64) Firefox/120" })).toBe("none");
    expect(installMode({ ...env, userAgent: "Mozilla/5.0 (Macintosh; Intel Mac OS X) Safari/605", platform: "MacIntel" })).toBe("none");
  });
  it("hides itself once the app is installed", () => {
    expect(installMode({ ...env, standalone: true, hasPrompt: true, userAgent: "Chrome" })).toBe("installed");
  });
});

describe("swipes and keyboard shortcuts", () => {
  it("reads a quick horizontal drag as a swipe, and ignores taps, scrolls and slow drags", () => {
    expect(swipeOf(-120, 10, 200)).toBe("left");
    expect(swipeOf(120, -10, 200)).toBe("right");
    expect(swipeOf(20, 0, 100)).toBeNull();
    expect(swipeOf(-90, 120, 200)).toBeNull();
    expect(swipeOf(-120, 5, 1500)).toBeNull();
  });

  const press = (key: string, target: { tagName?: string; type?: string; isContentEditable?: boolean } | null = { tagName: "DIV" }, mods = {}) =>
    shortcutFor({ key, target, ...mods });
  it("maps arrows and letters to actions", () => {
    expect(press("ArrowRight")).toBe("next");
    expect(press("ArrowLeft")).toBe("skip");
    expect(press("f")).toBe("favorite");
    expect(press("F")).toBe("favorite");
    expect(press("t")).toBe("table");
    expect(press("r")).toBe("speak");
    expect(press("x")).toBeNull();
  });
  it("stays out of the way while typing and of browser shortcuts", () => {
    expect(press("f", { tagName: "TEXTAREA" })).toBeNull();
    expect(press("f", { tagName: "INPUT", type: "text" })).toBeNull();
    expect(press("ArrowRight", { tagName: "SELECT" })).toBeNull();
    expect(press("f", { tagName: "DIV", isContentEditable: true })).toBeNull();
    expect(press("f", { tagName: "DIV" }, { ctrlKey: true })).toBeNull();
    expect(press("ArrowLeft", { tagName: "DIV" }, { altKey: true })).toBeNull();
  });
  it("leaves the arrow keys to a focused radio group, but still takes letters", () => {
    expect(press("ArrowRight", { tagName: "INPUT", type: "radio" })).toBeNull();
    expect(press("f", { tagName: "INPUT", type: "radio" })).toBe("favorite");
  });
});

describe("timer", () => {
  it("formats the clock", () => {
    expect(formatClock(0)).toBe("0:00");
    expect(formatClock(5)).toBe("0:05");
    expect(formatClock(65)).toBe("1:05");
    expect(formatClock(120)).toBe("2:00");
    expect(formatClock(-3)).toBe("0:00");
  });
  it("counts whole seconds left and never goes below zero", () => {
    expect(secondsLeft(10_000, 4_000)).toBe(6);
    expect(secondsLeft(10_000, 4_001)).toBe(6);
    expect(secondsLeft(10_000, 10_000)).toBe(0);
    expect(secondsLeft(10_000, 12_000)).toBe(0);
  });
  it("labels the choices", () => {
    expect(timerLabel(0)).toBe("Off");
    expect(timerLabel(30)).toBe("30 sec");
    expect(timerLabel(60)).toBe("1 min");
    expect(timerLabel(90)).toBe("1:30");
    expect(timerLabel(120)).toBe("2 min");
  });
});

describe("my own questions", () => {
  const fresh = () => createCustomStore(memoryStore(), () => new Date("2026-11-09T10:00:00Z"));

  it("adds, trims, remembers and removes a question", () => {
    const store = memoryStore();
    const mine = createCustomStore(store, () => new Date("2026-11-09T10:00:00Z"));
    const result = mine.add("  What was your first car?  ", 1);
    expect(result.ok).toBe(true);
    expect(mine.get()).toHaveLength(1);
    expect(mine.get()[0]).toMatchObject({ text: "What was your first car?", depth: 1 });
    expect(createCustomStore(store).get()).toHaveLength(1);
    mine.remove(mine.get()[0].id);
    expect(mine.get()).toHaveLength(0);
  });

  it("refuses empty, tiny, huge and duplicate questions, with a reason", () => {
    const mine = fresh();
    expect(mine.add("   ", 1)).toMatchObject({ ok: false });
    expect(mine.add("Hi?", 1)).toMatchObject({ ok: false });
    expect(mine.add("x".repeat(300), 1)).toMatchObject({ ok: false });
    mine.add("What was your first car?", 2);
    const dup = mine.add("what was your FIRST car?", 2);
    expect(dup).toMatchObject({ ok: false });
    expect(mine.get()).toHaveLength(1);
  });

  it("gives every question its own id, even after removing one", () => {
    const mine = fresh();
    mine.add("What was your first car?", 1);
    mine.add("What was your first pet called?", 1);
    const [a, b] = mine.get();
    expect(a.id).not.toBe(b.id);
    mine.remove(a.id);
    mine.add("What was your first concert?", 1);
    expect(new Set(mine.get().map((q) => q.id)).size).toBe(2);
  });

  it("stops at a limit, notifies subscribers, and survives blocked storage", () => {
    const mine = fresh();
    let heard = 0;
    mine.subscribe(() => heard++);
    for (let i = 0; i < 100; i++) mine.add(`Question number ${i} about something?`, 1);
    expect(mine.get()).toHaveLength(100);
    expect(mine.add("One question too many here?", 1)).toMatchObject({ ok: false });
    expect(heard).toBe(100);
    const memory = createCustomStore(blocked);
    expect(memory.add("Does this still work offline?", 3).ok).toBe(true);
    expect(memory.get()).toHaveLength(1);
  });

  it("plays like any other open question", () => {
    const mine = fresh();
    mine.add("What was your first car?", 3);
    expect(toOpenQuestion(mine.get()[0])).toMatchObject({ kind: "open", categoryId: "mine", depth: 3, text: "What was your first car?" });
  });
});

describe("seasonal packs", () => {
  it("has packs with ten different questions each", () => {
    expect(packs.length).toBeGreaterThanOrEqual(6);
    const ids = new Set<string>();
    const texts = new Set<string>();
    for (const pack of packs) {
      const qs = packQuestions(pack);
      expect(qs.length, pack.id).toBeGreaterThanOrEqual(10);
      for (const q of qs) {
        expect(q.text, q.id).toMatch(/\?$/);
        expect(ids.has(q.id), q.id).toBe(false);
        expect(texts.has(q.text.toLowerCase()), q.text).toBe(false);
        ids.add(q.id);
        texts.add(q.text.toLowerCase());
      }
      expect(new Set(qs.map((q) => q.depth)).size, `${pack.id} depths`).toBeGreaterThanOrEqual(3);
    }
  });

  it("knows which packs are in season, including across New Year", () => {
    const byId = (id: string) => packs.find((p) => p.id === id)!;
    expect(inSeason(byId("valentines"), new Date(2026, 1, 14))).toBe(true);
    expect(inSeason(byId("valentines"), new Date(2026, 6, 1))).toBe(false);
    expect(inSeason(byId("new-year"), new Date(2026, 11, 31))).toBe(true);
    expect(inSeason(byId("new-year"), new Date(2027, 0, 3))).toBe(true);
    expect(inSeason(byId("new-year"), new Date(2027, 5, 1))).toBe(false);
    expect(inSeason(byId("birthday"), new Date(2026, 4, 5))).toBe(false);
  });

  it("lists in-season packs first and labels each season", () => {
    const list = orderedPacks(new Date(2026, 9, 20));
    expect(list[0].id).toBe("spooky");
    expect(list).toHaveLength(packs.length);
    expect(seasonLabel(packs.find((p) => p.id === "valentines")!)).toBe("Feb 1 to Feb 20");
    expect(seasonLabel(packs.find((p) => p.id === "birthday")!)).toBe("Any day");
  });
});

describe("debate and trivia content", () => {
  it("has enough different motions", () => {
    expect(debateMotions.length).toBeGreaterThanOrEqual(24);
    expect(new Set(debateMotions.map((m) => m.toLowerCase())).size).toBe(debateMotions.length);
    for (const m of debateMotions) expect(m).toMatch(/[.]$/);
  });

  it("groups every trivia question into a topic with enough questions for a round", () => {
    const trivia = questions.filter((q) => q.kind === "trivia");
    for (const group of topicGroups) {
      expect(trivia.filter((q) => inTopicGroup(q, group.id)).length, group.label).toBeGreaterThanOrEqual(7);
    }
    for (const q of trivia) expect(topicGroups.some((g) => inTopicGroup(q, g.id)), q.id).toBe(true);
    expect(trivia.every((q) => inTopicGroup(q, "all"))).toBe(true);
  });
});

describe("relationship-type tags", () => {
  const open = questions.filter((q) => q.kind === "open");

  it("tags every question with at least one group", () => {
    for (const q of questions) expect(audiencesOf(q).length, q.id).toBeGreaterThan(0);
  });

  it("gives every group a real library, and every category some questions for the groups it suits", () => {
    for (const a of ["couple", "friends", "family", "team"] as const) {
      expect(open.filter((q) => matchesAudience(q, a)).length, a).toBeGreaterThan(150);
    }
    expect(questions.filter((q) => matchesAudience(q, "team") && q.categoryId === "icebreakers")).toHaveLength(50);
    expect(questions.filter((q) => matchesAudience(q, "couple") && q.categoryId === "love")).toHaveLength(50);
    expect(questions.filter((q) => matchesAudience(q, "family") && q.categoryId === "family")).toHaveLength(50);
  });

  it("keeps work questions for teams and partner questions for couples", () => {
    expect(audiencesOfEntry("icebreakers", 2, "What does a great manager do that helps you do your best work?")).toEqual(["team"]);
    expect(audiencesOfEntry("love", 4, "What do you need from me that you haven't been brave enough to say?")).toEqual(["couple"]);
    expect(audiencesOfEntry("debate", 3, "Is it ever acceptable to read your partner's messages?")).toEqual(["couple", "friends"]);
    expect(audiencesOfEntry("party", 3, "Who in this group do you secretly compete with the most?")).toEqual(["friends"]);
  });

  it("keeps the most personal questions away from a team meeting and a family dinner", () => {
    for (const q of open) {
      if (q.depth === 4 && q.categoryId !== "icebreakers" && q.categoryId !== "family") {
        expect(audiencesOf(q).includes("family") && !/\b(parents?|family|kids?|child)\b/i.test(q.text), q.id).toBe(false);
      }
      if (q.categoryId === "party" && q.depth >= 2) expect(audiencesOf(q), q.id).not.toContain("team");
    }
    expect(open.filter((q) => q.categoryId === "love" && audiencesOf(q).includes("team"))).toHaveLength(0);
  });

  it("treats 'everyone' as no filter", () => {
    for (const q of questions) expect(matchesAudience(q, "everyone")).toBe(true);
  });
});

describe("play sets", () => {
  it("builds a category's set, with a quiz limited to ten", () => {
    const love = categorySet("love", "everyone")!;
    expect(love.pool).toHaveLength(50);
    expect(love.limit).toBeNull();
    expect(love.key).toBe("play:love");
    expect(love.href).toBe("#/play/love");
    const trivia = categorySet("trivia", "everyone")!;
    expect(trivia.limit).toBe(10);
    expect(categorySet("nonsense", "everyone")).toBeNull();
  });

  it("narrows by group, and gives each choice its own saved progress", () => {
    const team = categorySet("deep", "team")!;
    expect(team.pool.length).toBeLessThan(50);
    expect(team.pool.length).toBeGreaterThan(10);
    expect(team.pool.every((q) => matchesAudience(q, "team"))).toBe(true);
    expect(team.key).toBe("play:deep:team");
    expect(categorySet("love", "team")!.pool).toHaveLength(0);
  });

  it("narrows trivia by topic, with a short topic making a short quiz", () => {
    const logic = categorySet("trivia", "everyone", "logic")!;
    expect(logic.key).toBe("play:trivia:t-logic");
    expect(logic.pool.length).toBeGreaterThanOrEqual(7);
    expect(logic.limit).toBe(Math.min(10, logic.pool.length));
    expect(logic.pool.every((q) => inTopicGroup(q, "logic"))).toBe(true);
    expect(categorySet("trivia", "team")!.pool).toHaveLength(50);
  });

  it("builds the surprise, pack and my-questions sets", () => {
    expect(surpriseSet("everyone").pool).toHaveLength(500);
    expect(surpriseSet("everyone").href).toBe("#/surprise");
    expect(surpriseSet("couple").key).toBe("surprise:couple");
    const spooky = packSet("spooky")!;
    expect(spooky.pool).toHaveLength(10);
    expect(spooky.key).toBe("pack:spooky");
    expect(packSet("nope")).toBeNull();
    const mine = createCustomStore(memoryStore());
    mine.add("What was your first car?", 1);
    expect(mineSet(mine.get()).pool).toHaveLength(1);
    expect(mineSet(mine.get()).key).toBe("mine");
  });

  it("turns a saved key back into its set", () => {
    expect(setFromKey(categoryKey("love", "couple"))?.pool.length).toBe(50);
    expect(setFromKey(categoryKey("trivia", "everyone", "science"))?.title).toMatch(/Trivia/);
    expect(setFromKey("surprise")?.pool).toHaveLength(500);
    expect(setFromKey("pack:birthday")?.pool).toHaveLength(10);
    expect(setFromKey("mine", [])?.pool).toHaveLength(0);
    expect(setFromKey("whatever")).toBeNull();
    expect(setFromKey("play:ghost")).toBeNull();
  });
});

describe("continue where you left off", () => {
  it("reports how far through a round someone is", () => {
    const store = memoryStore();
    const set = categorySet("love", "everyone")!;
    let s = startSession("love", set.pool, { random: seeded() });
    for (let i = 0; i < 4; i++) s = advance(s, set.pool);
    saveSession(set.key, s, store);
    const saved = JSON.parse(store.getItem(`closer.session.${set.key}`)!);
    expect(roundProgress(saved, set)).toEqual({ done: 5, total: 50, finished: false });
    expect(roundProgress(null, set)).toBeNull();
    expect(roundProgress({ junk: true }, set)).toBeNull();
  });

  it("counts a quiz against its length", () => {
    const set = categorySet("trivia", "everyone")!;
    const s = startSession("trivia", set.pool, { limit: set.limit, random: seeded() });
    expect(roundProgress(s, set)).toEqual({ done: 1, total: 10, finished: false });
  });

  it("remembers the last set played", () => {
    const store = memoryStore();
    expect(loadLastPlayed(store)).toBeNull();
    saveLastPlayed("play:love", store);
    expect(loadLastPlayed(store)).toBe("play:love");
    expect(loadLastPlayed(blocked)).toBeNull();
  });
});

describe("debate night", () => {
  const start = () => debate.startDebate(["Ana", "Ben"], debateMotions, 3, 60, seeded(4));
  /** One whole round, spoken and voted. */
  const playRound = (s: debate.DebateState, verdict: debate.Verdict) =>
    debate.castVote(debate.nextSpeaker(debate.nextSpeaker(debate.beginSpeeches(s))), verdict);

  it("starts with a motion for each round, and a few spare ones to swap in", () => {
    const s = start();
    expect(s.motions).toHaveLength(3);
    expect(new Set(s.motions).size).toBe(3);
    expect(s.spare.length).toBeGreaterThan(0);
    expect(s.phase).toBe("brief");
    expect(s.seconds).toBe(60);
  });

  it("assigns sides and swaps them every round", () => {
    expect([0, 1, 2, 3].map(debate.forPlayerOf)).toEqual([0, 1, 0, 1]);
    expect([0, 1, 2, 3].map(debate.againstPlayerOf)).toEqual([1, 0, 1, 0]);
  });

  it("walks through brief, the two speeches, the vote and the result, in order", () => {
    let s = debate.castVote(start(), "for"); // too early: nobody has spoken
    expect(s.phase).toBe("brief");
    s = debate.beginSpeeches(start());
    expect(s.phase).toBe("for");
    s = debate.nextSpeaker(s);
    expect(s.phase).toBe("against");
    s = debate.nextSpeaker(s);
    expect(s.phase).toBe("vote");
    s = debate.castVote(s, "against");
    expect(s.phase).toBe("result");
    expect(s.verdict).toBe("against");
  });

  it("scores the side the room picked, once, and nothing for a draw", () => {
    let s = playRound(start(), "for"); // round 0: Ana argues for
    expect(s.scores).toEqual([1, 0]);
    s = debate.castVote(s, "against");
    expect(s.scores).toEqual([1, 0]);
    s = playRound(debate.nextRound(s), "for"); // round 1: Ben argues for
    expect(s.scores).toEqual([1, 1]);
    s = playRound(debate.nextRound(s), "draw");
    expect(s.scores).toEqual([1, 1]);
  });

  it("ends with a winner, and replays from zero", () => {
    let s = start();
    for (let r = 0; r < 3; r++) {
      s = playRound(s, "for"); // the "for" side wins every round: Ana argues for in rounds 0 and 2, Ben in round 1
      s = debate.nextRound(s);
    }
    expect(s.phase).toBe("final");
    expect(s.scores).toEqual([2, 1]);
    expect(debate.winner(s)).toBe(0);
    expect(debate.winner({ ...s, scores: [2, 2] })).toBe("tie");
    const again = debate.replay(s, debateMotions, seeded(9));
    expect(again.scores).toEqual([0, 0]);
    expect(again.phase).toBe("brief");
  });

  it("swaps a motion for a spare one, only before the speeches", () => {
    const s = start();
    const swapped = debate.reroll(s);
    expect(swapped.motions[0]).not.toBe(s.motions[0]);
    expect(s.motions.includes(swapped.motions[0])).toBe(false);
    expect(swapped.spare).toHaveLength(s.spare.length - 1);
    const speaking = debate.beginSpeeches(s);
    expect(debate.reroll(speaking)).toBe(speaking);
  });
});
