import type { InstallMode } from "./install";
import type { Route } from "./router";
import { createSetting, isBoolean, type Setting } from "./settings";
import { browserStore, type KeyValueStore } from "./storage";
import { showsTabBar } from "./tabbar";

/** Whether the person has closed the install card, kept on the device so it never comes back. */
export const createInstallCardDismissed = (store: KeyValueStore | null = browserStore()): Setting<boolean> =>
  createSetting<boolean>("closer.installCard.dismissed", false, isBoolean, store);
export const installCardDismissed = createInstallCardDismissed();

/** The "Install Closer" card appears once someone has started a round (they know what they'd be
 *  installing), on a browser that can install, until they close it or install. */
export function shouldOfferInstallCard(input: { mode: InstallMode; started: boolean; dismissed: boolean }): boolean {
  if (!input.started || input.dismissed) return false;
  return input.mode === "prompt" || input.mode === "ios" || input.mode === "android";
}

/** The pages the card may sit on: the main pages (the ones with the tab bar), except About, which
 *  has its own "Install Closer" section. */
export const installCardFitsPage = (route: Route): boolean => showsTabBar(route) && route.page !== "about";
