/** Names for a game: blank ones become "Player 1", "Player 2"…, long ones are cut, and two players
 *  with the same name get a number so everyone can tell them apart. Names are only ever held in memory. */
export const MAX_NAME = 20;

export function cleanNames(raw: readonly string[], count: number): string[] {
  const seen = new Map<string, number>();
  return Array.from({ length: count }, (_, i) => {
    const base = (raw[i] ?? "").trim().slice(0, MAX_NAME) || `Player ${i + 1}`;
    const key = base.toLowerCase();
    const n = (seen.get(key) ?? 0) + 1;
    seen.set(key, n);
    return n === 1 ? base : `${base} ${n}`;
  });
}

/** The next seat around the table. */
export const nextSeat = (index: number, count: number): number => (index + 1) % count;

/** "Ana", "Ana and Ben", "Ana, Ben and Cy". */
export function joinNames(names: readonly string[]): string {
  if (names.length <= 1) return names[0] ?? "";
  return `${names.slice(0, -1).join(", ")} and ${names[names.length - 1]}`;
}
