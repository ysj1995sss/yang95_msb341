// Swipes on a phone and keys on a computer, as plain functions so they can be tested without a browser.

const MIN_SWIPE = 60;
const MAX_SWIPE_MS = 800;

/** A quick, mostly horizontal drag: "left" or "right". Taps, scrolls and slow drags are not swipes. */
export function swipeOf(dx: number, dy: number, ms: number): "left" | "right" | null {
  if (ms > MAX_SWIPE_MS || Math.abs(dx) < MIN_SWIPE || Math.abs(dx) < Math.abs(dy) * 1.5) return null;
  return dx < 0 ? "left" : "right";
}

export type Shortcut = "next" | "skip" | "favorite" | "table" | "speak";

export interface KeyInfo {
  key: string;
  ctrlKey?: boolean;
  metaKey?: boolean;
  altKey?: boolean;
  target: { tagName?: string; type?: string; isContentEditable?: boolean } | null;
}

const TEXT_INPUTS = new Set(["", "text", "search", "email", "url", "tel", "number", "password"]);

/** What a key press should do on a question card, or null to leave it alone. Typing in a field, a
 *  browser shortcut (Ctrl, Alt, Cmd), or an arrow on a focused radio group is never taken over. */
export function shortcutFor({ key, ctrlKey, metaKey, altKey, target }: KeyInfo): Shortcut | null {
  if (ctrlKey || metaKey || altKey) return null;
  const tag = (target?.tagName ?? "").toUpperCase();
  if (target?.isContentEditable || tag === "TEXTAREA" || tag === "SELECT") return null;
  const isInput = tag === "INPUT";
  if (isInput && TEXT_INPUTS.has((target?.type ?? "").toLowerCase())) return null;

  if (key === "ArrowRight") return isInput ? null : "next";
  if (key === "ArrowLeft") return isInput ? null : "skip";
  switch (key.toLowerCase()) {
    case "f": return "favorite";
    case "t": return "table";
    case "r": return "speak";
    default: return null;
  }
}
