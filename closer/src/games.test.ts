import { describe, expect, it } from "vitest";
import { fuseSeconds } from "./utils/games/bomb";
import { createDeck, pickMany } from "./utils/games/deck";
import { resolveTap } from "./utils/games/duel";
import { formatValue, isRight, pickPair, type FactGroup } from "./utils/games/higherLower";
import { compatLabel, matchCount, matchPercent } from "./utils/games/matching";
import { cleanNames, nextSeat } from "./utils/games/players";
import { createRoster, isOut, isOver, loseLife, nextIn, stillIn, winner } from "./utils/games/roster";
import { award, leaders, outcomeLine } from "./utils/games/scores";

/** A repeatable "random": cycles through the given numbers. */
const sequence = (...values: number[]) => { let i = 0; return () => values[i++ % values.length]!; };

describe("deck", () => {
  it("never repeats a card until the whole deck has been drawn", () => {
    const deck = createDeck(["a", "b", "c", "d"]);
    const first = [deck.draw(), deck.draw(), deck.draw(), deck.draw()];
    expect(new Set(first).size).toBe(4);
    expect(deck.remaining()).toBe(0);
  });

  it("reshuffles when empty, and the card just drawn is not drawn again straight away", () => {
    for (let run = 0; run < 50; run++) {
      const deck = createDeck([1, 2, 3]);
      const drawn = Array.from({ length: 9 }, () => deck.draw());
      for (let i = 1; i < drawn.length; i++) expect(drawn[i]).not.toBe(drawn[i - 1]);
    }
  });

  it("works with a single card and refuses an empty deck", () => {
    const deck = createDeck(["only"]);
    expect([deck.draw(), deck.draw()]).toEqual(["only", "only"]);
    expect(() => createDeck([])).toThrow();
  });

  it("picks several different items, never more than there are", () => {
    expect(new Set(pickMany([1, 2, 3, 4, 5], 3)).size).toBe(3);
    expect(pickMany([1, 2], 5)).toHaveLength(2);
  });
});

describe("player names", () => {
  it("fills blanks with Player 1, Player 2, trims and cuts long names", () => {
    expect(cleanNames(["  Ana ", "", "x".repeat(40)], 3)).toEqual(["Ana", "Player 2", "x".repeat(20)]);
  });

  it("tells two players with the same name apart", () => {
    expect(cleanNames(["Sam", "sam", "Sam"], 3)).toEqual(["Sam", "sam 2", "Sam 3"]);
  });

  it("goes round the table", () => {
    expect(nextSeat(0, 3)).toBe(1);
    expect(nextSeat(2, 3)).toBe(0);
  });
});

describe("elimination roster (Never Have I Ever, Last Word)", () => {
  const roster = createRoster(["A", "B", "C"], 2);

  it("takes lives off one player and never goes below zero", () => {
    const r = loseLife(loseLife(loseLife(roster, 1), 1), 1);
    expect(r.lives).toEqual([2, 0, 2]);
    expect(isOut(r, 1)).toBe(true);
    expect(roster.lives).toEqual([2, 2, 2]);
  });

  it("lists who is still in, and skips the ones who are out going round the table", () => {
    const r = loseLife(roster, 1, 2);
    expect(stillIn(r)).toEqual([0, 2]);
    expect(nextIn(r, 0)).toBe(2);
    expect(nextIn(r, 2)).toBe(0);
  });

  it("ends when one is left, and names the winner", () => {
    let r = loseLife(roster, 0, 2);
    expect(isOver(r)).toBe(false);
    expect(winner(r)).toBeNull();
    r = loseLife(r, 2, 2);
    expect(isOver(r)).toBe(true);
    expect(winner(r)).toBe(1);
  });

  it("has no winner when the last players go out together", () => {
    const r = loseLife(loseLife(createRoster(["A", "B"], 1), 0), 1);
    expect(isOver(r)).toBe(true);
    expect(winner(r)).toBeNull();
    expect(nextIn(r, 0)).toBeNull();
  });
});

describe("scores", () => {
  it("awards points to one player and finds the leaders", () => {
    const s = award(award([0, 0, 0], 1), 1, 2);
    expect(s).toEqual([0, 3, 0]);
    expect(leaders(s)).toEqual([1]);
    expect(leaders([2, 5, 5])).toEqual([1, 2]);
  });

  it("words the result, including ties", () => {
    expect(outcomeLine(["Ana", "Ben", "Cy"], [3, 1, 0])).toBe("Ana wins");
    expect(outcomeLine(["Ana", "Ben", "Cy"], [2, 2, 0])).toBe("Ana and Ben tie");
    expect(outcomeLine(["Ana", "Ben", "Cy"], [1, 1, 1])).toBe("Ana, Ben and Cy tie");
  });
});

describe("bomb fuse", () => {
  it("is always within the chosen range, both ends included", () => {
    expect(fuseSeconds(10, 25, () => 0)).toBe(10);
    expect(fuseSeconds(10, 25, () => 0.999999)).toBe(25);
    for (let i = 0; i < 200; i++) {
      const s = fuseSeconds(20, 45);
      expect(s).toBeGreaterThanOrEqual(20);
      expect(s).toBeLessThanOrEqual(45);
    }
  });
});

describe("matching answers (Match Game, Compatibility Quiz)", () => {
  it("counts the same choices position by position", () => {
    expect(matchCount([0, 1, 2, 3], [0, 2, 2, 1])).toBe(2);
  });

  it("turns it into a whole percentage, and 0 with nothing to compare", () => {
    expect(matchPercent([0, 1, 2], [0, 1, 0])).toBe(67);
    expect(matchPercent([1, 1], [1, 1])).toBe(100);
    expect(matchPercent([], [])).toBe(0);
  });

  it("always has a kind line for the result", () => {
    for (const p of [0, 20, 40, 60, 80, 95, 100]) expect(compatLabel(p).length).toBeGreaterThan(5);
    expect(compatLabel(100)).not.toBe(compatLabel(0));
  });
});

describe("Trivia Duel taps", () => {
  it("gives the round to whoever taps the right answer first", () => {
    expect(resolveTap(0, true)).toEqual({ winner: 0, byMistake: false });
    expect(resolveTap(1, true)).toEqual({ winner: 1, byMistake: false });
  });

  it("hands the round to the other player after a wrong tap", () => {
    expect(resolveTap(0, false)).toEqual({ winner: 1, byMistake: true });
    expect(resolveTap(1, false)).toEqual({ winner: 0, byMistake: true });
  });
});

describe("Higher or Lower", () => {
  const group: FactGroup = {
    id: "g", question: "How tall?", unit: "m", higher: "taller", lower: "shorter",
    facts: [{ name: "A", value: 10 }, { name: "B", value: 20 }, { name: "C", value: 20 }],
  };

  it("marks a guess right or wrong", () => {
    const [a, b] = [group.facts[0]!, group.facts[1]!];
    expect(isRight("higher", a, b)).toBe(true);
    expect(isRight("lower", a, b)).toBe(false);
    expect(isRight("lower", b, a)).toBe(true);
  });

  it("never pairs two facts with the same number", () => {
    for (let i = 0; i < 100; i++) {
      const [known, other] = pickPair(group);
      expect(known.value).not.toBe(other.value);
    }
    expect(pickPair(group, sequence(0))[0]).toBeDefined();
  });

  it("refuses a group where every number is the same", () => {
    expect(() => pickPair({ ...group, facts: [{ name: "A", value: 1 }, { name: "B", value: 1 }] })).toThrow();
  });

  it("writes numbers with thousands separators, and years plainly", () => {
    expect(formatValue(8849, "m")).toBe("8,849 m");
    expect(formatValue(1876, "year")).toBe("1876");
  });
});
