import { describe, expect, it } from "vitest";
import { dailyFor, localDateKey } from "./utils/daily";
import { sessionOrder } from "./utils/session";
import { loadAnswers, loadDailyAnswer, saveAnswer, saveDailyAnswer, type KeyValueStore } from "./utils/storage";

const list = [{ id: "a", text: "A?" }, { id: "b", text: "B?" }, { id: "c", text: "C?" }];

function memoryStore(): KeyValueStore {
  const data = new Map<string, string>();
  return { getItem: (k) => data.get(k) ?? null, setItem: (k, v) => void data.set(k, v) };
}

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

describe("a play session", () => {
  const ids = Array.from({ length: 12 }, (_, i) => `q${i}`);

  it("picks the requested number of questions, none twice", () => {
    const order = sessionOrder(ids, 10);
    expect(order).toHaveLength(10);
    expect(new Set(order).size).toBe(10);
    expect(order.every((id) => ids.includes(id))).toBe(true);
  });

  it("is shuffled by the random source it's given", () => {
    let seed = 1;
    const random = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
    const first = sessionOrder(ids, 10, random);
    seed = 1;
    expect(sessionOrder(ids, 10, random)).toEqual(first);
    expect(first).not.toEqual(ids.slice(0, 10));
  });

  it("uses every question when there are fewer than asked for", () => {
    expect(sessionOrder(["x", "y"], 10).sort()).toEqual(["x", "y"]);
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
    const broken: KeyValueStore = { getItem: () => { throw new Error("blocked"); }, setItem: () => { throw new Error("blocked"); } };
    expect(() => saveAnswer("x", "y", broken)).not.toThrow();
    expect(loadAnswers(broken)).toEqual({});
    expect(loadDailyAnswer("2026-10-25", broken)).toBeNull();
  });
});

import { parseRoute } from "./utils/router";

describe("page addresses", () => {
  it("map to pages", () => {
    expect(parseRoute("")).toEqual({ page: "home" });
    expect(parseRoute("#/")).toEqual({ page: "home" });
    expect(parseRoute("#/explore")).toEqual({ page: "explore" });
    expect(parseRoute("#/about/")).toEqual({ page: "about" });
    expect(parseRoute("#/play/would-you-rather")).toEqual({ page: "play", categoryId: "would-you-rather" });
    expect(parseRoute("#/nowhere")).toEqual({ page: "not-found" });
  });
});
