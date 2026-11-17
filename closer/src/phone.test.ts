import { describe, expect, it, vi } from "vitest";
import { gridSpans } from "./utils/gridSpans";
import { createInstallCardDismissed, installCardFitsPage, shouldOfferInstallCard } from "./utils/installCard";
import { href, parseRoute } from "./utils/router";
import { showsTabBar, tabFor, tabs } from "./utils/tabbar";
import { mainScriptOf, watchForUpdate } from "./utils/update";

describe("library address", () => {
  it("links to the library hub", () => {
    expect(href.library).toBe("#/library");
    expect(parseRoute(href.library)).toEqual({ page: "library" });
  });
});

describe("tab bar", () => {
  it("has the four places from the spec, in order", () => {
    expect(tabs.map((t) => t.label)).toEqual(["Home", "Explore", "Games", "Library"]);
    expect(tabs.map((t) => t.to)).toEqual([href.home, href.explore, href.games, href.library]);
  });

  it("shows on the top-level pages", () => {
    for (const hash of ["#/", "#/explore", "#/games", "#/library", "#/about", "#/favorites", "#/mine", "#/packs"]) {
      expect(showsTabBar(parseRoute(hash)), hash).toBe(true);
    }
  });

  it("hides while a round or a game is being played", () => {
    for (const hash of ["#/play/love", "#/guess", "#/debate", "#/surprise", "#/packs/winter-holidays", "#/favorites/play", "#/favorites/play/love", "#/mine/play", "#/games/truth-or-dare", "#/nowhere"]) {
      expect(showsTabBar(parseRoute(hash)), hash).toBe(false);
    }
  });

  it("lights the tab a page belongs under", () => {
    expect(tabFor(parseRoute("#/"))).toBe("home");
    expect(tabFor(parseRoute("#/explore"))).toBe("explore");
    expect(tabFor(parseRoute("#/games"))).toBe("games");
    expect(tabFor(parseRoute("#/games/truth-or-dare"))).toBe("games");
    for (const hash of ["#/library", "#/favorites", "#/mine", "#/packs"]) expect(tabFor(parseRoute(hash)), hash).toBe("library");
    expect(tabFor(parseRoute("#/about"))).toBeNull();
  });
});

describe("card grid spans", () => {
  const base = (n: number) => gridSpans(n).map((s) => s.base);
  const wide = (n: number) => gridSpans(n).map((s) => s.wide);
  /** A row-by-row fill of the grid: the number of free cells left in the last row. */
  const gaps = (spans: number[], columns: number) => (columns - (spans.reduce((a, b) => a + b, 0) % columns)) % columns;

  it("gives seven cards a full last row on two columns, and Love and Trivia double width on three", () => {
    expect(base(7)).toEqual([1, 1, 1, 1, 1, 1, 2]);
    expect(wide(7)).toEqual([2, 1, 1, 1, 1, 1, 2]);
  });

  it("never leaves a gap, for any number of visible cards", () => {
    for (let n = 1; n <= 12; n++) {
      expect(gaps(base(n), 2), `${n} cards on two columns`).toBe(0);
      expect(gaps(wide(n), 3), `${n} cards on three columns`).toBe(0);
    }
  });

  it("leaves a card alone when nothing needs filling, and handles no cards", () => {
    expect(base(6)).toEqual([1, 1, 1, 1, 1, 1]);
    expect(wide(6)).toEqual([1, 1, 1, 1, 1, 1]);
    expect(gridSpans(0)).toEqual([]);
    expect(wide(1)).toEqual([3]);
  });
});

describe("install card", () => {
  const ready = { mode: "ios", started: true, dismissed: false } as const;

  it("shows to a phone browser once someone has started a round", () => {
    expect(shouldOfferInstallCard(ready)).toBe(true);
    expect(shouldOfferInstallCard({ ...ready, mode: "android" })).toBe(true);
    expect(shouldOfferInstallCard({ ...ready, mode: "prompt" })).toBe(true);
  });

  it("waits for the first round, and stays away once installed or dismissed", () => {
    expect(shouldOfferInstallCard({ ...ready, started: false })).toBe(false);
    expect(shouldOfferInstallCard({ ...ready, dismissed: true })).toBe(false);
    expect(shouldOfferInstallCard({ ...ready, mode: "installed" })).toBe(false);
    expect(shouldOfferInstallCard({ ...ready, mode: "none" })).toBe(false);
  });

  it("remembers a dismissal on the device", () => {
    const memory: Record<string, string> = {};
    const store = { getItem: (k: string) => memory[k] ?? null, setItem: (k: string, v: string) => void (memory[k] = v) };
    const dismissed = createInstallCardDismissed(store);
    expect(dismissed.get()).toBe(false);
    dismissed.set(true);
    expect(createInstallCardDismissed(store).get()).toBe(true);
  });

  it("sits on the main pages, not on About (it has its own install section) or while playing", () => {
    for (const hash of ["#/", "#/explore", "#/games", "#/library", "#/favorites", "#/mine", "#/packs"]) expect(installCardFitsPage(parseRoute(hash)), hash).toBe(true);
    for (const hash of ["#/about", "#/play/love", "#/guess", "#/packs/winter-holidays"]) expect(installCardFitsPage(parseRoute(hash)), hash).toBe(false);
  });
});

describe("update notice", () => {
  const page = (script: string) => `<!doctype html><head><script type="module" crossorigin src="${script}"></script></head>`;

  it("reads the main script a built page names", () => {
    expect(mainScriptOf(page("./assets/index-AbC123.js"))).toBe("./assets/index-AbC123.js");
    expect(mainScriptOf('<script type="module" src="/src/main.tsx"></script>')).toBe("/src/main.tsx");
    expect(mainScriptOf("<p>no script</p>")).toBeNull();
  });

  it("offers a refresh when the page on the server names a different build", async () => {
    const watch = watchForUpdate({ running: "./assets/index-old.js", fetchPage: async () => page("./assets/index-new.js") });
    const seen = vi.fn();
    watch.subscribe(seen);
    await watch.check();
    expect(watch.get()).toBe(true);
    expect(seen).toHaveBeenCalledTimes(1);
    await watch.check();
    expect(seen).toHaveBeenCalledTimes(1);
  });

  it("stays quiet when the build is the same, when offline, or when the running script is unknown", async () => {
    const same = watchForUpdate({ running: "./assets/index-a.js", fetchPage: async () => page("./assets/index-a.js") });
    await same.check();
    expect(same.get()).toBe(false);
    const offline = watchForUpdate({ running: "./assets/index-a.js", fetchPage: () => Promise.reject(new Error("offline")) });
    await offline.check();
    expect(offline.get()).toBe(false);
    const unknown = watchForUpdate({ running: null, fetchPage: async () => page("./assets/index-b.js") });
    await unknown.check();
    expect(unknown.get()).toBe(false);
  });
});
