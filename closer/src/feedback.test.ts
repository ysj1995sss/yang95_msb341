import { describe, expect, it } from "vitest";
import { games, moodLabels } from "./data/games";
import { categorySet, surpriseSet } from "./data/playSets";
import { fitsFilter, fitsPlayers, isFiltered, loadGameFilter, NO_FILTER, saveGameFilter } from "./utils/gameFilter";
import { href, parseRoute } from "./utils/router";
import type { KeyValueStore } from "./utils/storage";

const memory = (): KeyValueStore => {
  const map = new Map<string, string>();
  return { getItem: (k) => map.get(k) ?? null, setItem: (k, v) => void map.set(k, v) };
};

describe("Games filter", () => {
  it("gives every game a player range that matches its label", () => {
    for (const g of games) {
      const m = g.players.match(/^(\d+)(?: to (\d+))? players?/);
      expect(m, g.id).not.toBeNull();
      expect(g.min, g.id).toBe(Number(m![1]));
      expect(g.max, g.id).toBe(Number(m![2] ?? m![1]));
      expect(g.moods.length, g.id).toBeGreaterThan(0);
      for (const mood of g.moods) expect(Object.keys(moodLabels)).toContain(mood);
    }
  });

  it("matches a group size to the games that take it", () => {
    const duo = { min: 2, max: 2, moods: [] };
    const party = { min: 3, max: 10, moods: [] };
    const solo = { min: 1, max: 6, moods: [] };
    expect(fitsPlayers(duo, "2")).toBe(true);
    expect(fitsPlayers(duo, "3-5")).toBe(false);
    expect(fitsPlayers(party, "2")).toBe(false);
    expect(fitsPlayers(party, "6+")).toBe(true);
    expect(fitsPlayers(solo, "1")).toBe(true);
    expect(fitsPlayers(duo, "1")).toBe(false);
    expect(fitsPlayers(duo, "any")).toBe(true);
  });

  it("filters by players and mood together", () => {
    const quickPair = { min: 2, max: 2, moods: ["quick", "competitive"] as const };
    expect(fitsFilter(quickPair, { players: "2", mood: "quick" })).toBe(true);
    expect(fitsFilter(quickPair, { players: "2", mood: "date" })).toBe(false);
    expect(fitsFilter(quickPair, NO_FILTER)).toBe(true);
    expect(isFiltered(NO_FILTER)).toBe(false);
    expect(isFiltered({ players: "any", mood: "silly" })).toBe(true);
  });

  it("has at least one game for every choice on its own", () => {
    for (const players of ["1", "2", "3-5", "6+"] as const) {
      expect(games.some((g) => fitsFilter(g, { players, mood: "any" })), players).toBe(true);
    }
    for (const mood of Object.keys(moodLabels) as (keyof typeof moodLabels)[]) {
      expect(games.some((g) => fitsFilter(g, { players: "any", mood })), mood).toBe(true);
    }
  });

  it("remembers the filter for the visit and ignores anything it doesn't know", () => {
    const store = memory();
    expect(loadGameFilter(store)).toEqual(NO_FILTER);
    saveGameFilter({ players: "2", mood: "date" }, store);
    expect(loadGameFilter(store)).toEqual({ players: "2", mood: "date" });
    store.setItem("closer.gamesFilter", JSON.stringify({ players: "99", mood: "spooky" }));
    expect(loadGameFilter(store)).toEqual(NO_FILTER);
    expect(loadGameFilter(null)).toEqual(NO_FILTER);
  });
});

describe("Help, trivia label and Surprise me wording", () => {
  it("opens the help page at #/help as well as #/about", () => {
    expect(parseRoute(href.help)).toEqual({ page: "about" });
    expect(parseRoute("#/about")).toEqual({ page: "about" });
  });

  it("gives the trivia set a fixed quiz length to show on its card", () => {
    expect(categorySet("trivia")?.limit).toBe(10);
  });

  it("says when Surprise me is narrowed to one group", () => {
    expect(surpriseSet("team").description).toMatch(/suit teams/);
    expect(surpriseSet("everyone").description).toMatch(/^A random mix from all \d+ questions/);
  });
});
