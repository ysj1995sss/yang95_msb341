import { describe, expect, it } from "vitest";
import { NavLog } from "./utils/navigation";
import { clearSavedRounds, loadLastPlayed, saveLastPlayed } from "./utils/resume";
import { loadSession, saveSession, type RemovableStore } from "./utils/storage";
import { IDLE_MS, startVisit, touchVisit } from "./utils/visit";

function memoryStore(): RemovableStore & { keys(): string[] } {
  const map = new Map<string, string>();
  return {
    getItem: (k) => map.get(k) ?? null,
    setItem: (k, v) => void map.set(k, v),
    removeItem: (k) => void map.delete(k),
    get length() { return map.size; },
    key: (i) => [...map.keys()][i] ?? null,
    keys: () => [...map.keys()],
  };
}

describe("opening the app again starts a fresh shuffle", () => {
  const T0 = 1_000_000;

  it("forgets saved rounds on the first open, and keeps favorites", () => {
    const local = memoryStore();
    const session = memoryStore();
    saveSession("love", { done: false }, local);
    saveLastPlayed("love", local);
    local.setItem("closer.favorites", JSON.stringify(["a"]));
    expect(startVisit(T0, session, local)).toBe(true);
    expect(loadSession("love", local)).toBeNull();
    expect(loadLastPlayed(local)).toBeNull();
    expect(local.getItem("closer.favorites")).toBe(JSON.stringify(["a"]));
  });

  it("keeps the round on a refresh or a quick return", () => {
    const local = memoryStore();
    const session = memoryStore();
    startVisit(T0, session, local);
    saveSession("love", { done: false }, local);
    saveLastPlayed("love", local);
    expect(startVisit(T0 + 60_000, session, local)).toBe(false);
    expect(loadSession("love", local)).toEqual({ done: false });
    expect(loadLastPlayed(local)).toBe("love");
  });

  it("treats a long idle gap as opening the app again", () => {
    const local = memoryStore();
    const session = memoryStore();
    startVisit(T0, session, local);
    saveSession("love", { done: false }, local);
    touchVisit(T0 + 1000, session);
    expect(startVisit(T0 + 1000 + IDLE_MS + 1, session, local)).toBe(true);
    expect(loadSession("love", local)).toBeNull();
  });

  it("treats a new browser session as a new visit even when rounds were saved long ago", () => {
    const local = memoryStore();
    saveSession("love", { done: false }, local);
    expect(startVisit(T0, memoryStore(), local)).toBe(true);
    expect(loadSession("love", local)).toBeNull();
  });

  it("does not crash when storage is blocked", () => {
    expect(() => startVisit(T0, null, null)).not.toThrow();
    expect(startVisit(T0, null, null)).toBe(true);
    expect(() => clearSavedRounds(null)).not.toThrow();
  });

  it("clears only rounds, not other saved keys", () => {
    const local = memoryStore();
    saveSession("a", 1, local);
    saveSession("b", 2, local);
    local.setItem("closer.favorites", "[]");
    local.setItem("closer.tour", "1");
    clearSavedRounds(local);
    expect(local.keys().sort()).toEqual(["closer.favorites", "closer.tour"]);
  });
});

describe("going back returns to where you were", () => {
  it("opens pages fresh at the top and numbers them", () => {
    const log = new NavLog(memoryStore());
    expect(log.arrive(undefined, "#/")).toEqual({ kind: "push", index: 0, scrollY: 0 });
    log.leave(900);
    expect(log.arrive(undefined, "#/debate")).toEqual({ kind: "push", index: 1, scrollY: 0 });
  });

  it("returns to the saved spot when going back", () => {
    const log = new NavLog(memoryStore());
    log.arrive(undefined, "#/");
    log.leave(900);
    log.arrive(undefined, "#/debate");
    log.leave(40);
    expect(log.arrive(0, "#/")).toEqual({ kind: "revisit", index: 0, scrollY: 900 });
    log.leave(950);
    expect(log.arrive(1, "#/debate")).toEqual({ kind: "revisit", index: 1, scrollY: 40 });
  });

  it("forgets the spots ahead when a new page is opened after going back", () => {
    const log = new NavLog(memoryStore());
    log.arrive(undefined, "#/");
    log.leave(500);
    log.arrive(undefined, "#/explore");
    log.leave(300);
    log.arrive(0, "#/");
    log.leave(500);
    expect(log.arrive(undefined, "#/games")).toEqual({ kind: "push", index: 1, scrollY: 0 });
    log.leave(10);
    expect(log.arrive(0, "#/").scrollY).toBe(500);
  });

  it("does not trust a history number that points at a different page", () => {
    const log = new NavLog(memoryStore());
    log.arrive(undefined, "#/");
    log.arrive(undefined, "#/explore");
    expect(log.arrive(0, "#/games").kind).toBe("push");
  });

  it("finds the page before this one, whatever the link's trailing slash", () => {
    const log = new NavLog(memoryStore());
    expect(log.previousPath()).toBeNull();
    log.arrive(undefined, "#/games");
    log.arrive(undefined, "#/games/truth-or-dare");
    expect(log.isPrevious("#/games")).toBe(true);
    expect(log.isPrevious("#/games/")).toBe(true);
    expect(log.isPrevious("#/explore")).toBe(false);
    expect(log.isPrevious("#/")).toBe(false);
  });

  it("treats the empty address and '#/' as the home page", () => {
    const log = new NavLog(memoryStore());
    log.arrive(undefined, "");
    log.arrive(undefined, "#/about");
    expect(log.isPrevious("#/")).toBe(true);
  });

  it("survives a reload through its saved copy", () => {
    const store = memoryStore();
    const first = new NavLog(store);
    first.arrive(undefined, "#/");
    first.leave(700);
    first.arrive(undefined, "#/explore");
    first.leave(20);
    const reloaded = new NavLog(store);
    expect(reloaded.arrive(1, "#/explore")).toEqual({ kind: "revisit", index: 1, scrollY: 20 });
    expect(reloaded.arrive(0, "#/")).toEqual({ kind: "revisit", index: 0, scrollY: 700 });
  });

  it("ignores a damaged saved copy", () => {
    const store = memoryStore();
    store.setItem("closer.nav", "{not json");
    expect(new NavLog(store).arrive(undefined, "#/")).toEqual({ kind: "push", index: 0, scrollY: 0 });
    store.setItem("closer.nav", JSON.stringify({ paths: [1, 2], scroll: {} }));
    expect(new NavLog(store).arrive(0, "#/").kind).toBe("push");
  });

  it("works with no storage at all", () => {
    const log = new NavLog(null);
    log.arrive(undefined, "#/");
    log.leave(100);
    log.arrive(undefined, "#/debate");
    expect(log.arrive(0, "#/")).toEqual({ kind: "revisit", index: 0, scrollY: 100 });
  });
});
