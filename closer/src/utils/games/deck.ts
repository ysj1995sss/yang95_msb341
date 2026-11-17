import { shuffle } from "../shuffle";

/** A shuffled stack of cards that never repeats until every card has been drawn, then reshuffles
 *  (without putting the card just drawn straight back on top). */
export interface Deck<T> {
  draw(): T;
  /** Cards left before the next reshuffle. */
  remaining(): number;
}

export function createDeck<T>(items: readonly T[], random: () => number = Math.random): Deck<T> {
  if (items.length === 0) throw new Error("A deck needs at least one card");
  let pile = shuffle(items, random);
  let last: T | undefined;
  return {
    draw() {
      if (pile.length === 0) {
        pile = shuffle(items, random);
        if (items.length > 1 && pile[pile.length - 1] === last) [pile[0], pile[pile.length - 1]] = [pile[pile.length - 1]!, pile[0]!];
      }
      last = pile.pop() as T;
      return last;
    },
    remaining: () => pile.length,
  };
}

/** `count` different items from `items`, in random order (fewer if there aren't enough). */
export function pickMany<T>(items: readonly T[], count: number, random: () => number = Math.random): T[] {
  return shuffle(items, random).slice(0, count);
}
