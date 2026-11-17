// Pass the Bomb: a fuse of unknown length runs while the phone is passed round. Whoever holds it
// when it goes off loses.

/** A whole number of seconds from `min` to `max`, both included. */
export function fuseSeconds(min: number, max: number, random: () => number = Math.random): number {
  return min + Math.floor(random() * (max - min + 1));
}

export const FUSE_RANGES = {
  short: { label: "Short", min: 10, max: 25 },
  medium: { label: "Medium", min: 20, max: 45 },
  long: { label: "Long", min: 35, max: 70 },
} as const;

export type FuseLength = keyof typeof FUSE_RANGES;
