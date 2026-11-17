/** How many answers two people gave the same choice for (compared position by position). */
export function matchCount(a: readonly number[], b: readonly number[]): number {
  return a.reduce((n, x, i) => (b[i] === x ? n + 1 : n), 0);
}

/** A whole-number percentage of matching answers; 0 when there were none to compare. */
export function matchPercent(a: readonly number[], b: readonly number[]): number {
  const total = Math.min(a.length, b.length);
  return total === 0 ? 0 : Math.round((matchCount(a, b) / total) * 100);
}

/** A friendly line for the compatibility result. It is a game, so every band is kind. */
export function compatLabel(percent: number): string {
  if (percent >= 90) return "Practically one mind";
  if (percent >= 75) return "Very in sync";
  if (percent >= 55) return "A great mix of alike and different";
  if (percent >= 35) return "Opposites who keep it interesting";
  return "Total opposites, so much to learn from each other";
}
