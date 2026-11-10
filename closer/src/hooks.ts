import { useCallback, useEffect, useRef, useState, useSyncExternalStore, type RefObject } from "react";
import { customQuestions, type CustomQuestion } from "./utils/custom";
import { currentInstallMode, promptInstall, subscribeInstall, type InstallMode } from "./utils/install";
import type { Setting } from "./utils/settings";
import { shortcutFor, swipeOf, type Shortcut } from "./utils/gestures";
import { favorites } from "./utils/storage";
import { applyTheme, isThemeChoice, resolveTheme, themeSetting, type Theme } from "./utils/theme";
import { secondsLeft } from "./utils/timer";

/** The hearted question ids, re-rendering whenever one is added or removed. */
export function useFavorites(): readonly string[] {
  return useSyncExternalStore(favorites.subscribe, favorites.get);
}

/** A remembered choice, re-rendering whenever it changes. */
export function useSetting<T>(setting: Setting<T>): T {
  return useSyncExternalStore(setting.subscribe, setting.get);
}

/** The questions the player wrote. */
export function useCustomQuestions(): readonly CustomQuestion[] {
  return useSyncExternalStore(customQuestions.subscribe, customQuestions.get);
}

/** What the install button should offer here, and how to trigger the browser's install dialog. */
export function useInstall(): { mode: InstallMode; install: () => Promise<"accepted" | "dismissed" | "unavailable"> } {
  const mode = useSyncExternalStore(subscribeInstall, currentInstallMode, () => "none" as InstallMode);
  return { mode, install: promptInstall };
}

const systemDarkQuery = () => (typeof window === "undefined" ? null : window.matchMedia?.("(prefers-color-scheme: dark)") ?? null);

/** Light or dark: the person's choice, or the device's when they haven't chosen. Also paints the page. */
export function useTheme(): { theme: Theme; toggle: () => void } {
  const choice = useSetting(themeSetting);
  const [systemDark, setSystemDark] = useState(() => systemDarkQuery()?.matches ?? false);
  useEffect(() => {
    const query = systemDarkQuery();
    if (!query) return;
    const onChange = () => setSystemDark(query.matches);
    query.addEventListener("change", onChange);
    return () => query.removeEventListener("change", onChange);
  }, []);
  const theme = resolveTheme(isThemeChoice(choice) ? choice : "system", systemDark);
  useEffect(() => applyTheme(theme), [theme]);
  return { theme, toggle: () => themeSetting.set(theme === "dark" ? "light" : "dark") };
}

export interface Countdown {
  seconds: number;
  left: number;
  running: boolean;
  finished: boolean;
  start: () => void;
  pause: () => void;
  reset: () => void;
}

/** A countdown from `seconds`. It starts when asked, and starts over whenever `resetKey` changes
 *  (a new question) or the length does. It counts against the clock, so a busy tab doesn't drift. */
export function useCountdown(seconds: number, resetKey: unknown): Countdown {
  const [state, setState] = useState<{ endAt: number | null; left: number }>({ endAt: null, left: seconds });

  useEffect(() => setState({ endAt: null, left: seconds }), [seconds, resetKey]);

  useEffect(() => {
    const endAt = state.endAt;
    if (endAt === null) return;
    const id = window.setInterval(() => {
      const left = secondsLeft(endAt, Date.now());
      setState((s) => (s.endAt === endAt ? { endAt: left === 0 ? null : endAt, left } : s));
    }, 200);
    return () => window.clearInterval(id);
  }, [state.endAt]);

  const finished = seconds > 0 && state.left === 0;
  useEffect(() => {
    if (finished) navigator.vibrate?.(300);
  }, [finished]);

  const start = useCallback(() => setState((s) => {
    const left = s.left > 0 ? s.left : seconds;
    return { endAt: Date.now() + left * 1000, left };
  }), [seconds]);
  const pause = useCallback(() => setState((s) => (s.endAt === null ? s : { endAt: null, left: secondsLeft(s.endAt, Date.now()) })), []);
  const reset = useCallback(() => setState({ endAt: null, left: seconds }), [seconds]);

  return { seconds, left: state.left, running: state.endAt !== null, finished, start, pause, reset };
}

/** Arrow keys, F, T and R on a question card. Handlers can change on every render.
 *
 *  The keys only work while keyboard focus is inside `scope` (the play area), never anywhere else on
 *  the page. That keeps single-letter shortcuts from firing by accident for people using speech
 *  input or assistive technology (WCAG 2.1.4, Character Key Shortcuts). */
export function useShortcuts(handlers: Partial<Record<Shortcut, () => void>>, enabled: boolean, scope: RefObject<HTMLElement | null>): void {
  const latest = useRef(handlers);
  useEffect(() => { latest.current = handlers; });
  useEffect(() => {
    const element = scope.current;
    if (!enabled || !element) return;
    const onKey = (event: KeyboardEvent) => {
      const action = shortcutFor({
        key: event.key, ctrlKey: event.ctrlKey, metaKey: event.metaKey, altKey: event.altKey, target: event.target as HTMLElement | null,
      });
      const run = action ? latest.current[action] : undefined;
      if (run) {
        event.preventDefault();
        run();
      }
    };
    element.addEventListener("keydown", onKey);
    return () => element.removeEventListener("keydown", onKey);
  }, [enabled, scope]);
}

/** Touch handlers that report a quick left or right swipe. Spread them on the element to watch. */
export function useSwipe(onSwipe: (direction: "left" | "right") => void, enabled = true) {
  const start = useRef<{ x: number; y: number; t: number } | null>(null);
  return {
    onTouchStart: (e: React.TouchEvent) => {
      const t = e.touches[0];
      start.current = enabled && t ? { x: t.clientX, y: t.clientY, t: Date.now() } : null;
    },
    onTouchEnd: (e: React.TouchEvent) => {
      const from = start.current;
      const t = e.changedTouches[0];
      start.current = null;
      if (!from || !t) return;
      const direction = swipeOf(t.clientX - from.x, t.clientY - from.y, Date.now() - from.t);
      if (direction) onSwipe(direction);
    },
  };
}
