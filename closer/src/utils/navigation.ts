import { browserStore, type KeyValueStore, read, write } from "./storage";
import { sessionStore } from "./visit";

// Going back should land where the person was, not at the top of the page. Every page the person
// opens is numbered in the browser's history entry; where they had scrolled to is kept per number.
// Opening a page fresh starts at the top; coming back to one (the Back button, or a "Back to…" link,
// which is turned into the same thing) returns to the saved spot.

const KEY = "closer.nav";

interface Saved {
  /** The address (without "#") of each numbered entry. */
  paths: string[];
  /** How far each numbered entry had been scrolled when it was left. */
  scroll: Record<number, number>;
}

export interface Arrival {
  /** "push": a page opened fresh. "revisit": back, forward or a reload of a page seen before. */
  kind: "push" | "revisit";
  /** The number to store in the history entry. */
  index: number;
  /** Where to scroll to; 0 for a page opened fresh. */
  scrollY: number;
}

const pathOf = (hash: string): string => hash.replace(/^#/, "").replace(/\/+$/, "") || "/";

export class NavLog {
  private paths: string[] = [];
  private scroll: Record<number, number> = {};
  private current: number | null = null;

  constructor(private readonly store: KeyValueStore | null) {
    const saved = read<Partial<Saved>>(KEY, store);
    if (saved && Array.isArray(saved.paths) && saved.paths.every((p) => typeof p === "string")) {
      this.paths = saved.paths;
      this.scroll = saved.scroll && typeof saved.scroll === "object" ? saved.scroll : {};
    }
  }

  /** The page just arrived at, given the number found in its history entry (if any). */
  arrive(entryIndex: unknown, hash: string): Arrival {
    const path = pathOf(hash);
    if (typeof entryIndex === "number" && this.paths[entryIndex] === path) {
      this.current = entryIndex;
      return { kind: "revisit", index: entryIndex, scrollY: this.scroll[entryIndex] ?? 0 };
    }
    const index = this.current === null ? 0 : this.current + 1;
    this.paths.length = index;
    this.paths[index] = path;
    for (const key of Object.keys(this.scroll)) if (Number(key) >= index) delete this.scroll[Number(key)];
    this.current = index;
    this.save();
    return { kind: "push", index, scrollY: 0 };
  }

  /** Remembers how far the page being left was scrolled. */
  leave(scrollY: number): void {
    if (this.current === null) return;
    this.scroll[this.current] = Math.max(0, Math.round(scrollY));
    this.save();
  }

  /** The address of the page before this one in the visit, or null at the first page. */
  previousPath(): string | null {
    return this.current !== null && this.current > 0 ? (this.paths[this.current - 1] ?? null) : null;
  }

  /** Whether a link to `hash` leads to the page just before this one. */
  isPrevious(hash: string): boolean {
    return this.previousPath() === pathOf(hash);
  }

  private save(): void {
    write(KEY, { paths: this.paths, scroll: this.scroll } satisfies Saved, this.store);
  }
}

/** Scrolls to `y`, trying again for a moment in case the page is still taking its full height.
 *  Returns a function that stops trying. */
export function restoreScroll(y: number, frames = 45): () => void {
  let id = 0;
  let left = frames;
  const step = () => {
    // "instant" so a page that scrolls smoothly by default does not glide there while it is still settling.
    window.scrollTo({ top: y, behavior: "instant" });
    left -= 1;
    if (Math.abs(window.scrollY - y) < 2 || left <= 0) return;
    id = window.requestAnimationFrame(step);
  };
  step();
  return () => window.cancelAnimationFrame(id);
}

let log: NavLog | null = null;
let arrival: Arrival = { kind: "push", index: 0, scrollY: 0 };

/** How the page now showing was reached. Stays the same until the next page change. */
export const currentArrival = (): Arrival => arrival;

/** Writes the page's number into its history entry, so going back to it later is recognized.
 *  Called again once the page has rendered, because some browsers (an address-bar change, for one)
 *  finish adding the entry only after the change event. */
export function stampEntry(): void {
  if (window.history.state?.closerIndex === arrival.index) return;
  try {
    window.history.replaceState({ ...(window.history.state ?? {}), closerIndex: arrival.index }, "");
  } catch {
    // Some embedded browsers refuse; going back then simply starts at the top.
  }
}

function arrived(): void {
  if (!log) return;
  arrival = log.arrive(window.history.state?.closerIndex, window.location.hash);
  stampEntry();
}

/** Sets up scroll memory. Call once, before the app renders, so the page being left is measured
 *  before the next one replaces it. */
export function watchNavigation(): void {
  if (log) return;
  log = new NavLog(sessionStore() ?? browserStore());
  try {
    window.history.scrollRestoration = "manual";
  } catch {
    // Older browsers keep their own restoring, which is fine.
  }
  arrived();

  window.addEventListener("hashchange", () => {
    log?.leave(window.scrollY);
    arrived();
  });
  // Also when the page is hidden or closed: opening the same address again can drop the entry's number.
  const remember = () => { log?.leave(window.scrollY); stampEntry(); };
  window.addEventListener("pagehide", remember);
  document.addEventListener("visibilitychange", () => { if (document.visibilityState === "hidden") remember(); });

  // A "Back to …" link that leads to the page just before this one behaves like the Back button,
  // so that page comes back as it was (and the history does not grow a loop).
  document.addEventListener("click", (event) => {
    if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    const link = event.target instanceof Element ? event.target.closest<HTMLAnchorElement>("a[href^='#/']") : null;
    if (!link || (link.target && link.target !== "_self") || link.hasAttribute("download")) return;
    const target = link.getAttribute("href") ?? "";
    if (log?.isPrevious(target)) {
      event.preventDefault();
      window.history.back();
    }
  });
}
