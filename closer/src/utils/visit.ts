import { clearSavedRounds } from "./resume";
import type { KeyValueStore, RemovableStore } from "./storage";
import { browserStore } from "./storage";

// A round is kept while the app stays in use (a refresh, a trip to another page, a quick switch to
// another app), but opening Closer again starts every set on a fresh shuffle. With hundreds of
// questions in a set, picking up the old round would keep showing the same ones first.

/** How long the app can sit unused before the next look at it counts as opening it again. */
export const IDLE_MS = 30 * 60 * 1000;

const MARKER = "closer.visit";

export function sessionStore(): KeyValueStore | null {
  try {
    return typeof window !== "undefined" ? window.sessionStorage : null;
  } catch {
    return null;
  }
}

/** Notes that the app is in use right now. */
export function touchVisit(now: number, session: KeyValueStore | null = sessionStore()): void {
  try {
    session?.setItem(MARKER, String(now));
  } catch {
    // Blocked storage: every open then counts as a new visit, which is the safe direction.
  }
}

/** Called when the app opens, and again when it comes back to the front. When this is a new visit
 *  (the app was closed, or sat idle too long) every saved round is forgotten. Returns whether it was. */
export function startVisit(
  now: number,
  session: KeyValueStore | null = sessionStore(),
  local: RemovableStore | null = browserStore(),
): boolean {
  let last = Number.NaN;
  try {
    last = Number(session?.getItem(MARKER));
  } catch {
    // Treated as never seen.
  }
  const fresh = !Number.isFinite(last) || last <= 0 || now - last > IDLE_MS;
  if (fresh) clearSavedRounds(local);
  touchVisit(now, session);
  return fresh;
}

/** Keeps the visit marker current, and starts a new visit when the app returns after sitting idle. */
export function watchVisit(): void {
  startVisit(Date.now());
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "hidden") touchVisit(Date.now());
    else startVisit(Date.now());
  });
  window.addEventListener("pagehide", () => touchVisit(Date.now()));
}
