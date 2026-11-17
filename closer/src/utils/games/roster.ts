// Elimination games (Never Have I Ever, Last Word, Pass the Bomb): everyone starts with some
// lives; losing the last one puts you out; the last one standing wins.

export interface Roster {
  names: readonly string[];
  lives: readonly number[];
}

export const createRoster = (names: readonly string[], lives: number): Roster => ({ names, lives: names.map(() => lives) });

/** Takes `amount` lives from one player (never below zero). */
export function loseLife(roster: Roster, index: number, amount = 1): Roster {
  return { ...roster, lives: roster.lives.map((l, i) => (i === index ? Math.max(0, l - amount) : l)) };
}

export const isOut = (roster: Roster, index: number): boolean => (roster.lives[index] ?? 0) <= 0;

export const stillIn = (roster: Roster): number[] => roster.lives.flatMap((l, i) => (l > 0 ? [i] : []));

/** The game is over once one player (or nobody) is left. */
export const isOver = (roster: Roster): boolean => stillIn(roster).length <= 1;

/** The only player left, or null while it goes on or when the last players went out together. */
export function winner(roster: Roster): number | null {
  const left = stillIn(roster);
  return left.length === 1 ? left[0]! : null;
}

/** The next player still in, going round the table from `from`; null when nobody is. */
export function nextIn(roster: Roster, from: number): number | null {
  const n = roster.lives.length;
  for (let step = 1; step <= n; step++) {
    const i = (from + step) % n;
    if (!isOut(roster, i)) return i;
  }
  return null;
}
