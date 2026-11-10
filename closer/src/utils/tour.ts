import { createSetting } from "./settings";

// The first-launch tour: three short screens saying what Closer is, how to play, and how to make it
// yours. It shows once, on the home page, and can be replayed from the About page.

export interface TourStep {
  title: string;
  text: string;
  /** A short line of keys or gestures, shown under the text. */
  tip?: string;
}

export const tourSteps: readonly TourStep[] = [
  {
    title: "Welcome to Closer",
    text: "A free app of questions and games for couples, friends, families and teams. Read a question out loud, talk it over, and see where the conversation goes.",
  },
  {
    title: "Pick a mood, then play",
    text: "Choose an experience, set how deep to go from Fun & Light to Bold, and tap Next. Skip any question you like. Surprise me mixes everything.",
    tip: "On a computer, use the arrow keys. On a phone, swipe the card.",
  },
  {
    title: "Make it yours",
    text: "Heart the questions you love, write your own, and play two-player games on one device. Add Closer to your home screen and it works without a connection.",
  },
];

const isBoolean = (v: unknown): v is boolean => typeof v === "boolean";

/** True once the tour has been finished or skipped. */
export const tourSeen = createSetting<boolean>("closer.tour", false, isBoolean);

let replaying = false;
const listeners = new Set<() => void>();
const notify = () => listeners.forEach((l) => l());

export const subscribeTour = (l: () => void) => {
  listeners.add(l);
  const stop = tourSeen.subscribe(l);
  return () => { listeners.delete(l); stop(); };
};

/** Opens the tour again, for the "Replay the tour" button. */
export function replayTour(): void {
  replaying = true;
  notify();
}

export function closeTour(): void {
  replaying = false;
  tourSeen.set(true);
  notify();
}

export const isReplaying = (): boolean => replaying;
