// "Install Closer": what to offer depends on the browser. Chrome, Edge and Android Chrome hand the
// page an install prompt it can trigger from a button; iPhone and iPad have no prompt, so they get a
// short "Share, then Add to Home Screen" hint; an installed app shows nothing.

export type InstallMode = "installed" | "prompt" | "ios" | "android" | "none";

export interface InstallEnv {
  /** Already running as an installed app (a home-screen icon, not a browser tab). */
  standalone: boolean;
  /** The browser has offered an install prompt we are holding on to. */
  hasPrompt: boolean;
  userAgent: string;
  platform?: string;
  maxTouchPoints?: number;
}

export function installMode(env: InstallEnv): InstallMode {
  if (env.standalone) return "installed";
  if (env.hasPrompt) return "prompt";
  // iPadOS pretends to be a Mac, but a Mac with a touch screen is an iPad.
  const ios = /iPhone|iPad|iPod/i.test(env.userAgent) || (env.platform === "MacIntel" && (env.maxTouchPoints ?? 0) > 1);
  if (ios) return "ios";
  if (/Android/i.test(env.userAgent)) return "android";
  return "none";
}

// ---- The browser side ------------------------------------------------------------------------

interface BeforeInstallPromptEvent extends Event {
  prompt(): Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

let deferred: BeforeInstallPromptEvent | null = null;
let listening = false;
const listeners = new Set<() => void>();
const notify = () => listeners.forEach((l) => l());

/** Starts listening for the browser's install offer. Call once at start-up: the offer can arrive
 *  before any screen has asked for it, so it is kept until a button wants it. */
export function listenForInstall(): void {
  if (listening || typeof window === "undefined") return;
  listening = true;
  window.addEventListener("beforeinstallprompt", (event) => {
    event.preventDefault();
    deferred = event as BeforeInstallPromptEvent;
    notify();
  });
  window.addEventListener("appinstalled", () => {
    deferred = null;
    notify();
  });
  window.matchMedia?.("(display-mode: standalone)").addEventListener?.("change", notify);
}

export function currentInstallMode(): InstallMode {
  if (typeof window === "undefined") return "none";
  const nav = window.navigator as Navigator & { standalone?: boolean };
  return installMode({
    standalone: window.matchMedia?.("(display-mode: standalone)").matches === true || nav.standalone === true,
    hasPrompt: deferred !== null,
    userAgent: nav.userAgent,
    platform: nav.platform,
    maxTouchPoints: nav.maxTouchPoints,
  });
}

export function subscribeInstall(listener: () => void): () => void {
  listeners.add(listener);
  return () => void listeners.delete(listener);
}

/** Shows the browser's own install dialog. */
export async function promptInstall(): Promise<"accepted" | "dismissed" | "unavailable"> {
  const event = deferred;
  if (!event) return "unavailable";
  deferred = null;
  notify();
  await event.prompt();
  const { outcome } = await event.userChoice;
  return outcome;
}
