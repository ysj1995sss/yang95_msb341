import { describe, expect, it } from "vitest";
import { claims, factGroups, priceItems } from "./data/games/brain";
import { budgets, dateIdeas, moods } from "./data/games/dates";
import { captionScenes, productProblems, productTwists, storyStarters } from "./data/games/creative";
import { compatibilityQuestions, matchPrompts, memoryLane, thisOrThat } from "./data/games/know";
import { dares, lastWordTopics, mostLikelyTo, neverHaveIEver, rapidFire } from "./data/games/party";
import { duelQuestions, spiceLabels, truthPool, type Spice } from "./data/games/pools";
import { gameById, gameGroups, games } from "./data/games";
import { gameScreens } from "./pages/gameplay";
import { pickPair } from "./utils/games/higherLower";
import { joinNames } from "./utils/games/players";
import { href, parseRoute } from "./utils/router";

const distinct = (items: readonly string[]) => new Set(items.map((t) => t.trim().toLowerCase())).size === items.length;
const filled = (items: readonly string[]) => items.every((t) => t.trim().length > 3);

describe("the game list", () => {
  it("has the sixteen new games, each with a screen, a group and its own address", () => {
    expect(games).toHaveLength(16);
    expect(Object.keys(gameScreens).sort()).toEqual(games.map((g) => g.id).sort());
    expect(new Set(games.map((g) => g.id)).size).toBe(16);
    const groups = new Set(gameGroups.map((g) => g.id));
    for (const g of games) {
      expect(groups.has(g.group), g.id).toBe(true);
      expect(gameById(g.id)).toBe(g);
      expect(parseRoute(href.game(g.id))).toEqual({ page: "game", gameId: g.id });
    }
  });

  it("puts something in every group", () => {
    for (const group of gameGroups) expect(games.some((g) => g.group === group.id), group.id).toBe(true);
  });

  it("reads unknown game addresses as a game page the app then answers with Page not found", () => {
    expect(parseRoute("#/games/nope")).toEqual({ page: "game", gameId: "nope" });
    expect(gameScreens["nope"]).toBeUndefined();
  });
});

describe("party game content", () => {
  it("has enough different, filled-in prompts for a long night", () => {
    const sets: [string, readonly string[], number][] = [
      ["dares", dares, 150], ["never have i ever", neverHaveIEver, 150], ["most likely to", mostLikelyTo, 150], ["last word", lastWordTopics, 120], ["rapid fire", rapidFire, 150],
    ];
    for (const [name, items, least] of sets) {
      expect(items.length, name).toBeGreaterThanOrEqual(least);
      expect(distinct(items), `${name} has no duplicates`).toBe(true);
      expect(filled(items), name).toBe(true);
    }
  });

  it("writes each prompt as the whole sentence the screen shows", () => {
    for (const t of neverHaveIEver) expect(t, t).toMatch(/^Never have I ever .+\.$/);
    for (const t of mostLikelyTo) expect(t, t).toMatch(/^Who is most likely to .+\?$/);
    for (const t of rapidFire) expect(t, t).toMatch(/\?$/);
  });

  it("has a truth question pool for every spice, getting bigger as it gets bolder", () => {
    const sizes = (Object.keys(spiceLabels) as Spice[]).map((s) => truthPool(s).length);
    expect(sizes[0]).toBeGreaterThanOrEqual(30);
    expect(sizes[0]).toBeLessThanOrEqual(sizes[1]!);
    expect(sizes[1]).toBeLessThanOrEqual(sizes[2]!);
  });
});

describe("know-each-other content", () => {
  it("gives every choice question two to four different options", () => {
    for (const [name, set, count, options] of [["this or that", thisOrThat, 100, 2], ["match", matchPrompts, 80, 4], ["compatibility", compatibilityQuestions, 60, 4]] as const) {
      expect(set.length, name).toBeGreaterThanOrEqual(count);
      for (const p of set) {
        expect(p.options.length, p.text).toBe(options);
        expect(new Set(p.options).size, p.text).toBe(p.options.length);
      }
      expect(distinct(set.map((p) => p.text)), `${name} has no duplicates`).toBe(true);
    }
  });

  it("has memory prompts that are whole questions, ready to read out", () => {
    expect(memoryLane.length).toBeGreaterThanOrEqual(120);
    expect(distinct(memoryLane)).toBe(true);
    for (const m of memoryLane) expect(m, m).toMatch(/^Remember .*\?$/);
  });
});

describe("make-something content", () => {
  it("has story starters, captioned scenes and invention prompts", () => {
    expect(storyStarters.length).toBeGreaterThanOrEqual(75);
    expect(captionScenes.length).toBeGreaterThanOrEqual(75);
    expect(productProblems.length).toBeGreaterThanOrEqual(100);
    expect(productTwists.length).toBeGreaterThanOrEqual(50);
    for (const s of captionScenes) { expect(s.emoji.length).toBeGreaterThan(0); expect(s.setup.length).toBeGreaterThan(10); }
    expect(distinct(storyStarters) && distinct(productProblems) && distinct(productTwists)).toBe(true);
  });
});

describe("brain game content", () => {
  it("mixes true and made-up claims, each with a reason", () => {
    const real = claims.filter((c) => c.isTrue).length;
    expect(claims.length).toBeGreaterThanOrEqual(120);
    expect(real).toBeGreaterThan(claims.length * 0.35);
    expect(real).toBeLessThan(claims.length * 0.65);
    for (const c of claims) expect(c.why.length, c.text).toBeGreaterThan(10);
    expect(distinct(claims.map((c) => c.text))).toBe(true);
  });

  it("has number groups that can always make a pair with different values", () => {
    expect(factGroups.length).toBeGreaterThanOrEqual(15);
    for (const group of factGroups) {
      expect(group.facts.length, group.id).toBeGreaterThanOrEqual(6);
      for (let run = 0; run < 25; run++) {
        const [known, other] = pickPair(group);
        expect(known.value, group.id).not.toBe(other.value);
      }
    }
  });

  it("has prices with four different options and an answer that points at one", () => {
    expect(priceItems.length).toBeGreaterThanOrEqual(60);
    for (const p of priceItems) {
      expect(p.options, p.item).toHaveLength(4);
      expect(new Set(p.options).size, p.item).toBe(4);
      expect(p.options[p.answer], p.item).toBeDefined();
    }
  });

  it("has enough trivia for the longest duel (15 questions, no Expert ones), each with a valid answer", () => {
    const pool = duelQuestions.filter((q) => q.depth <= 3);
    expect(pool.length).toBeGreaterThanOrEqual(90);
    for (const q of duelQuestions) expect(q.options[q.answer], q.id).toBeDefined();
  });
});

describe("date ideas", () => {
  it("covers every budget and mood, so any filter lands on something", () => {
    for (const b of budgets) for (const m of moods) {
      const n = dateIdeas.filter((d) => d.budget === b && d.mood === m).length;
      expect(n, `${b} / ${m}`).toBeGreaterThanOrEqual(8);
    }
    expect(dateIdeas.length).toBeGreaterThanOrEqual(140);
    expect(distinct(dateIdeas.map((d) => d.text))).toBe(true);
  });
});

describe("names", () => {
  it("joins names for a sentence", () => {
    expect(joinNames([])).toBe("");
    expect(joinNames(["Ana"])).toBe("Ana");
    expect(joinNames(["Ana", "Ben"])).toBe("Ana and Ben");
    expect(joinNames(["Ana", "Ben", "Cy"])).toBe("Ana, Ben and Cy");
  });
});
