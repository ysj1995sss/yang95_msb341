import type { CategoryTint } from "../types";

/** A category's pastel background and matching border. Written out in full so Tailwind can see every
 *  class; the colors themselves live in index.css, light and dark. */
export const tintClass: Record<CategoryTint, string> = {
  rose: "bg-tint-rose border-tint-rose-line",
  lavender: "bg-tint-lavender border-tint-lavender-line",
  yellow: "bg-tint-yellow border-tint-yellow-line",
  peach: "bg-tint-peach border-tint-peach-line",
  mint: "bg-tint-mint border-tint-mint-line",
  sky: "bg-tint-sky border-tint-sky-line",
};

/** The look of a set with no single category (surprise, packs, favorites, your own questions). */
export const neutralTone = "bg-surface border-plum-100";
