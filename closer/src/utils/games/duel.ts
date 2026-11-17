// Trivia Duel: two players face each other over one phone and race to tap the right answer. The first
// tap decides the round: a right answer wins it, a wrong one hands it to the other player.

export type Seat = 0 | 1;

export interface DuelRound {
  winner: Seat;
  /** True when the winner got it by the other player tapping a wrong answer. */
  byMistake: boolean;
}

export function resolveTap(seat: Seat, correct: boolean): DuelRound {
  return correct ? { winner: seat, byMistake: false } : { winner: seat === 0 ? 1 : 0, byMistake: true };
}
