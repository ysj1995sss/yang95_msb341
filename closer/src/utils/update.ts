// "New version available". Every load of the page fetches the newest files first (see public/sw.js),
// so a fresh load is always up to date. The stale case is an app that is kept alive in the background
// (a phone resuming the installed app) still running the code it started with. So whenever the page
// comes back into view, it fetches the page again and compares the main script it names with the one
// that is running: a different one means a new deploy, and the page offers a refresh.

export interface UpdateWatch {
  get(): boolean;
  subscribe(listener: () => void): () => void;
}

/** The built main script a page names, e.g. "./assets/index-AbC123.js", or null. */
export function mainScriptOf(html: string): string | null {
  const tag = html.match(/<script\b[^>]*\btype="module"[^>]*>/i)?.[0];
  return tag?.match(/\bsrc="([^"]+)"/)?.[1] ?? null;
}

export interface UpdateSource {
  /** The main script this page is running. */
  running: string | null;
  /** Fetches the newest copy of the page's HTML, bypassing caches. */
  fetchPage(): Promise<string>;
}

export interface UpdateChecker extends UpdateWatch {
  /** Looks for a new deploy. Network errors (offline) are ignored. */
  check(): Promise<void>;
}

export function watchForUpdate(source: UpdateSource): UpdateChecker {
  let available = false;
  const listeners = new Set<() => void>();
  return {
    get: () => available,
    subscribe(listener) {
      listeners.add(listener);
      return () => void listeners.delete(listener);
    },
    async check() {
      if (available || !source.running) return;
      let latest: string | null;
      try {
        latest = mainScriptOf(await source.fetchPage());
      } catch {
        return;
      }
      if (!latest || latest === source.running) return;
      available = true;
      listeners.forEach((l) => l());
    },
  };
}

let current: UpdateChecker | null = null;
const idle: UpdateWatch = { get: () => false, subscribe: () => () => undefined };

/** Starts watching for new deploys: checks each time the page comes back into view. Call once. */
export function startUpdateWatch(): void {
  if (current || typeof document === "undefined") return;
  const running = document.querySelector<HTMLScriptElement>('script[type="module"][src]')?.getAttribute("src") ?? null;
  const watch = watchForUpdate({
    running,
    fetchPage: async () => {
      const response = await fetch("./index.html", { cache: "no-store" });
      if (!response.ok) throw new Error(String(response.status));
      return response.text();
    },
  });
  current = watch;
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible") void watch.check();
  });
}

export const updateWatch = (): UpdateWatch => current ?? idle;
