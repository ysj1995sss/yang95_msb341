/** Adds points for one player. */
export function award(scores: readonly number[], index: number, points = 1): number[] {
  return scores.map((s, i) => (i === index ? s + points : s));
}

/** The player or players with the most points (everyone, when nobody has scored). */
export function leaders(scores: readonly number[]): number[] {
  const top = Math.max(...scores);
  return scores.flatMap((s, i) => (s === top ? [i] : []));
}

/** "Ana wins", "Ana and Ben tie", "Ana, Ben and Cy tie". */
export function outcomeLine(names: readonly string[], scores: readonly number[]): string {
  const top = leaders(scores).map((i) => names[i]!);
  if (top.length === 1) return `${top[0]} wins`;
  return `${top.slice(0, -1).join(", ")} and ${top[top.length - 1]} tie`;
}
