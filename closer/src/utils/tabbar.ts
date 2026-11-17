import { href, type Route } from "./router";

// The tab bar is the phone's way around: four main places, fixed to the bottom of the screen. It is
// left out while a round or a game is on, so it never crowds the question or the Next button.

export type TabId = "home" | "explore" | "games" | "library";

export const tabs: readonly { id: TabId; label: string; to: string }[] = [
  { id: "home", label: "Home", to: href.home },
  { id: "explore", label: "Explore", to: href.explore },
  { id: "games", label: "Games", to: href.games },
  { id: "library", label: "Library", to: href.library },
];


/** The tab a page belongs under, or null for a page that is not under any (About). */
export function tabFor(route: Route): TabId | null {
  switch (route.page) {
    case "home": return "home";
    case "explore": return "explore";
    case "games": return "games";
    case "library": case "favorites": case "mine": case "packs": return "library";
    default: return null;
  }
}

/** The tab bar shows on every page that sits under a tab, and on About. */
export const showsTabBar = (route: Route): boolean => tabFor(route) !== null || route.page === "about";
