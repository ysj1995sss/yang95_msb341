import { describe, expect, it } from "vitest";
import { audiencesOf, matchesAudience } from "./data/audience";
import { choiceBank, choiceTopics } from "./data/choices/bank";
import { debateMotions, isMotion } from "./data/debateMotions";
import { duelQuestions } from "./data/games/pools";
import { categorySet, surpriseSet } from "./data/playSets";
import { questionById, questions, questionsFor } from "./data/questions";
import { sourceUrl } from "./data/trivia/bank";
import { inTopicGroup, topicGroups } from "./data/triviaTopics";
import type { Depth, OpenQuestion, TriviaQuestion } from "./types";
import { defaultCeiling, matchChoices, planChoices } from "./utils/choices";
import { createSeenLog } from "./utils/seen";
import { advance, discuss, previous, recordOutcome, restoreSession, startSession } from "./utils/session";
import type { KeyValueStore } from "./utils/storage";
import { mixFor, planRound, unseenCount } from "./utils/triviaRound";

const memory = (): KeyValueStore => {
  const map = new Map<string, string>();
  return { getItem: (k) => map.get(k) ?? null, setItem: (k, v) => void map.set(k, v) };
};
const seeded = (seed = 1) => () => { seed = (seed * 16807) % 2147483647; return seed / 2147483647; };
const norm = (s: string) => s.toLowerCase().replace(/[^\p{L}\p{N} ]/gu, " ").replace(/\s+/g, " ").trim();
const STOP = new Set("would you rather the a an of and or in on to is are it be have has do does did for with at by as from that this than your you they who what which was were how many more most better should can could people one only always never every".split(" "));
const words = (s: string) => new Set(norm(s).split(" ").filter((w) => !STOP.has(w)));
const overlap = (a: Set<string>, b: Set<string>) => [...a].filter((w) => b.has(w)).length / Math.max(1, new Set([...a, ...b]).size);

const trivia = questionsFor("trivia") as TriviaQuestion[];
const choices = [...questionsFor("would-you-rather"), ...questionsFor("debate")] as OpenQuestion[];

describe("trivia bank", () => {
  it("has at least 1,000 questions, close to 100 in each of ten topics, every difficulty in each", () => {
    expect(trivia.length).toBeGreaterThanOrEqual(1000);
    expect(topicGroups).toHaveLength(10);
    for (const g of topicGroups) {
      const inGroup = trivia.filter((q) => inTopicGroup(q, g.id));
      expect(inGroup.length, g.label).toBeGreaterThanOrEqual(95);
      for (const [d, least] of [[1, 28], [2, 25], [3, 18], [4, 8]] as const) {
        expect(inGroup.filter((q) => q.depth === d).length, `${g.label} level ${d}`).toBeGreaterThanOrEqual(least);
      }
    }
    for (const q of trivia) expect(topicGroups.filter((g) => inTopicGroup(q, g.id)), q.id).toHaveLength(1);
  });

  it("gives every question a unique id and text, four different options, one answer, an explanation and a source", () => {
    expect(new Set(trivia.map((q) => q.id)).size).toBe(trivia.length);
    expect(new Set(trivia.map((q) => norm(q.text))).size).toBe(trivia.length);
    for (const q of trivia) {
      expect(q.options, q.id).toHaveLength(4);
      expect(q.options.every((o) => typeof o === "string" && o.trim() === o && o.length > 0), q.id).toBe(true);
      // "′" and "−" matter in a few answers, so options are compared as written.
      expect(new Set(q.options.map((o) => o.toLowerCase())).size, q.text).toBe(4);
      expect([0, 1, 2, 3], q.id).toContain(q.answer);
      expect([1, 2, 3, 4], q.id).toContain(q.depth);
      expect(q.explanation, q.id).toMatch(/[.!]$/);
      expect(q.explanation.length, q.text).toBeGreaterThanOrEqual(15);
      expect(q.source, q.id).toBeTruthy();
      expect(sourceUrl(q), q.id).toMatch(/^https:\/\/en\.wikipedia\.org\/wiki\/\S+$/);
    }
  });

  it("has no near-duplicates: the same answer asked for in nearly the same words", () => {
    const w = trivia.map((q) => words(q.text));
    const alike: string[] = [];
    for (let i = 0; i < trivia.length; i++) for (let j = 0; j < i; j++) {
      const same = norm(trivia[i]!.options[trivia[i]!.answer]!) === norm(trivia[j]!.options[trivia[j]!.answer]!);
      if (same && overlap(w[i]!, w[j]!) >= 0.5) alike.push(`${trivia[j]!.text} / ${trivia[i]!.text}`);
    }
    expect(alike).toEqual([]);
  });

  it("spreads the right answer over all four positions", () => {
    const where = [0, 0, 0, 0];
    for (const q of trivia) where[q.answer]++;
    for (const n of where) expect(n).toBeGreaterThan(trivia.length * 0.2);
  });

  it("is what the Trivia Duel plays, and stays out of the Surprise me mix", () => {
    expect(duelQuestions).toHaveLength(trivia.length);
    expect(surpriseSet().pool).toHaveLength(500);
  });
});

describe("planning a round", () => {
  it("makes a mixed ten: four Easy, three Medium, two Hard, one Expert, getting harder, topics varied", () => {
    for (let seed = 1; seed < 30; seed++) {
      const round = planRound(trivia, { length: 10, random: seeded(seed) });
      const depths = round.map((q) => q.depth);
      expect(depths).toEqual([1, 1, 1, 1, 2, 2, 2, 3, 3, 4]);
      expect(new Set(round.map((q) => q.topic)).size).toBeGreaterThanOrEqual(8);
      for (let i = 1; i < 10; i++) expect(round[i]!.topic).not.toBe(round[i - 1]!.topic);
    }
  });

  it("splits other lengths so they always add up", () => {
    for (const n of [0, 1, 3, 5, 7, 10, 15, 20]) expect(Object.values(mixFor(n)).reduce((a, b) => a + b, 0)).toBe(n);
  });

  it("respects a chosen difficulty and topic, and copes with a small or empty pool", () => {
    const expert = planRound(trivia, { length: 10, level: 4 });
    expect(expert.every((q) => q.depth === 4)).toBe(true);
    const food = trivia.filter((q) => inTopicGroup(q, "food"));
    expect(planRound(food, { length: 10 }).every((q) => q.topic === "Food & drink")).toBe(true);
    expect(planRound(food.slice(0, 3), { length: 10 })).toHaveLength(3);
    expect(planRound([], { length: 10 })).toEqual([]);
  });

  it("never repeats until the pool is used up, then brings back the longest-ago first", () => {
    const pool = trivia.filter((q) => inTopicGroup(q, "science"));
    const log = createSeenLog("t", memory());
    const asked: string[] = [];
    while (unseenCount(pool, log.all()) >= 10) {
      const round = planRound(pool, { length: 10, seen: log.all() });
      for (const q of round) { expect(asked).not.toContain(q.id); asked.push(q.id); log.add(q.id); }
    }
    expect(asked.length).toBeGreaterThanOrEqual(pool.length - 9);
    const left = unseenCount(pool, log.all());
    const last = planRound(pool, { length: 10, seen: log.all() });
    expect(last).toHaveLength(10);
    expect(last.filter((q) => !asked.includes(q.id))).toHaveLength(left);
    last.forEach((q) => log.add(q.id));
    expect(unseenCount(pool, log.all())).toBe(0);
    expect(planRound(pool, { length: 10, seen: log.all() })).toHaveLength(10);
    log.forget(pool.map((q) => q.id));
    expect(unseenCount(pool, log.all())).toBe(pool.length);
  });

  it("keeps the seen list in storage, survives damage, and works with none", () => {
    const store = memory();
    createSeenLog("k", store).add("a");
    expect(createSeenLog("k", store).all()).toEqual(["a"]);
    store.setItem("k", "{broken");
    expect(createSeenLog("k", store).all()).toEqual([]);
    const none = createSeenLog("k", null);
    none.add("x");
    expect(none.all()).toEqual(["x"]);
  });

  it("restores a planned round of ten, and still refuses a whole-pool set that lost questions", () => {
    const set = categorySet("trivia")!;
    const order = planRound(trivia, { length: 10 }).map((q) => q.id);
    let s = startSession("trivia", set.pool, { limit: set.limit, order });
    s = advance(recordOutcome(s, "correct"), set.pool);
    expect(restoreSession(JSON.parse(JSON.stringify(s)), "trivia", set.pool, set.limit)).toEqual(s);
    expect(restoreSession({ ...s, order: [...order, "nope"] }, "trivia", set.pool, set.limit)).toBeNull();
    const love = categorySet("love")!;
    const whole = startSession("love", love.pool);
    expect(restoreSession({ ...whole, order: whole.order.slice(1) }, "love", love.pool, null)).toBeNull();
    while (!s.done) s = advance(recordOutcome(s, "correct"), set.pool);
    expect(s.seen).toEqual(order);
  });
});

describe("Would You Rather and debates bank", () => {
  const of = (format: string) => choices.filter((q) => q.categoryId === format);

  it("has at least 500 of each format and 48 or more of each in every topic", () => {
    expect(of("would-you-rather").length).toBeGreaterThanOrEqual(500);
    expect(of("debate").length).toBeGreaterThanOrEqual(500);
    for (const t of choiceTopics) for (const f of ["would-you-rather", "debate"]) {
      expect(of(f).filter((q) => q.topic === t.id).length, `${t.label} ${f}`).toBeGreaterThanOrEqual(48);
    }
  });

  it("has unique ids and texts, and a topic and an intensity on every prompt", () => {
    expect(new Set(choices.map((q) => q.id)).size).toBe(choices.length);
    expect(new Set(choices.map((q) => norm(q.text))).size).toBe(choices.length);
    for (const q of choices) {
      expect(choiceTopics.some((t) => t.id === q.topic), q.id).toBe(true);
      expect([1, 2, 3, 4], q.id).toContain(q.depth);
      expect(q.text, q.id).toMatch(/^[A-Z].{13,168}[?.]$/u);
      expect(audiencesOf(q).length, q.id).toBeGreaterThan(0);
      expect(questionById(q.id), q.id).toBe(q);
    }
    for (const q of choiceBank) if (q.text.startsWith("Would you rather")) expect(q.text, q.id).toMatch(/ or /);
  });

  it("has no near-duplicates within a format", () => {
    const alike: string[] = [];
    for (const f of ["would-you-rather", "debate"]) {
      const list = of(f), w = list.map((q) => words(q.text));
      for (let i = 0; i < list.length; i++) for (let j = 0; j < i; j++) {
        if (w[i]!.size > 1 && w[j]!.size > 1 && overlap(w[i]!, w[j]!) >= 0.5) alike.push(`${list[j]!.id} "${list[j]!.text}" ~ ${list[i]!.id} "${list[i]!.text}"`);
      }
    }
    expect(alike).toEqual([]);
  });

  it("never puts a Bold prompt in front of a team or a family", () => {
    for (const q of choices) if (q.depth === 4) for (const a of ["team", "family"] as const) expect(matchesAudience(q, a), q.text).toBe(false);
  });

  it("filters by format, topic, group and intensity, and starts teams and families gently", () => {
    const team = categorySet("would-you-rather", "team")!;
    const got = matchChoices(team.pool, { format: "debate", topic: "money", ceiling: 2 });
    expect(got.length).toBeGreaterThan(10);
    for (const q of got) {
      expect([q.categoryId, q.topic]).toEqual(["debate", "money"]);
      expect(q.depth).toBeLessThanOrEqual(2);
      expect(matchesAudience(q, "team")).toBe(true);
    }
    expect([defaultCeiling("team"), defaultCeiling("family"), defaultCeiling("everyone"), defaultCeiling("couple")]).toEqual([2, 2, 3, 3]);
    for (const a of ["everyone", "couple", "friends", "family", "team"] as const) for (const t of choiceTopics) {
      const n = matchChoices(categorySet("would-you-rather", a)!.pool, { format: "both", topic: t.id, ceiling: defaultCeiling(a) }).length;
      expect(n, `${a} ${t.label}`).toBeGreaterThanOrEqual(20);
    }
  });

  it("plans sets that start light, deepen within the limit, mix formats and topics, and don't repeat", () => {
    for (const ceiling of [1, 2, 3, 4] as Depth[]) {
      const pool = matchChoices(categorySet("would-you-rather")!.pool, { format: "both", topic: "all", ceiling });
      const seen: string[] = [];
      for (let round = 0; round < 5; round++) {
        const ids = planChoices(pool, { length: 20, ceiling, seen, random: seeded(round + 3) });
        const qs = ids.map((id) => questionById(id) as OpenQuestion);
        expect(qs).toHaveLength(20);
        expect(qs.map((q) => q.depth)).toEqual(qs.map((q) => q.depth).sort());
        expect(qs[0]!.depth).toBe(1);
        expect(Math.max(...qs.map((q) => q.depth))).toBe(ceiling);
        expect(qs.filter((q) => q.categoryId === "debate").length).toBe(10);
        expect(new Set(qs.map((q) => q.topic)).size).toBe(10);
        for (let i = 1; i < 20; i++) expect(qs[i]!.topic).not.toBe(qs[i - 1]!.topic);
        for (const id of ids) expect(seen).not.toContain(id);
        seen.push(...ids);
      }
    }
  });

  it("steps back to the previous prompt and forward to the same one again", () => {
    const set = categorySet("would-you-rather")!;
    const order = planChoices(matchChoices(set.pool, { format: "both", topic: "all", ceiling: 3 }), { length: 20, ceiling: 3, seen: [] });
    const a = startSession("would-you-rather", set.pool, { limit: set.limit, order });
    expect(previous(a)).toBe(a);
    const b = discuss(a, set.pool);
    const back = previous(b);
    expect(back.currentId).toBe(a.currentId);
    expect(back.outcomes).toEqual({});
    expect(discuss(back, set.pool)).toEqual(b);
    expect(restoreSession(JSON.parse(JSON.stringify(b)), "would-you-rather", set.pool, set.limit)).toEqual(b);
  });

  it("gives Debate Night plenty of statements and yes-or-no questions in every topic", () => {
    for (const t of choiceTopics) {
      const n = of("debate").filter((q) => q.topic === t.id && q.depth <= 2 && isMotion(q.text)).length;
      expect(n, t.label).toBeGreaterThanOrEqual(12);
    }
    expect(isMotion("Is soup a drink?")).toBe(true);
    expect(isMotion("Renting or buying a home: which is the smarter move?")).toBe(false);
    expect(debateMotions.every(isMotion)).toBe(true);
  });
});

describe("the whole collection", () => {
  it("has no id used twice", () => {
    expect(new Set(questions.map((q) => q.id)).size).toBe(questions.length);
  });
});
