import type { DailyQuestion } from "../types";

/** The person's own calendar date, "YYYY-MM-DD", not UTC (an evening in the Americas is already
 *  tomorrow in UTC). */
export function localDateKey(date: Date): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

/** Today's question: the same all day, the next one tomorrow, round and round the list. */
export function dailyFor<T extends DailyQuestion>(date: Date, list: T[]): { question: T; dateKey: string } {
  const day = Math.floor(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()) / 86_400_000);
  return { question: list[((day % list.length) + list.length) % list.length], dateKey: localDateKey(date) };
}
