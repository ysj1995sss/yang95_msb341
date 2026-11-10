import { createSetting } from "./settings";

/** Seconds for the optional countdown; 0 is off. */
export const TIMER_CHOICES: readonly number[] = [0, 30, 60, 90, 120];

export const isTimerChoice = (value: unknown): value is number => typeof value === "number" && TIMER_CHOICES.includes(value);

export const timerSetting = createSetting<number>("closer.timer", 0, isTimerChoice);

export function formatClock(seconds: number): string {
  const s = Math.max(0, Math.floor(seconds));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

/** Whole seconds left until `endAt` (milliseconds), never below zero. */
export function secondsLeft(endAt: number, now: number): number {
  return Math.max(0, Math.ceil((endAt - now) / 1000));
}

export function timerLabel(seconds: number): string {
  if (seconds === 0) return "Off";
  if (seconds === 30) return "30 sec";
  if (seconds === 60) return "1 min";
  if (seconds === 120) return "2 min";
  return formatClock(seconds);
}
