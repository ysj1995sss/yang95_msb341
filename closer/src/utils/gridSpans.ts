// How wide each card in a card grid is, so the last row is always full, whatever number of cards
// the audience filter leaves. The grid has two columns on a phone and three on a wide screen.

export interface CardSpan {
  /** Columns the card takes on the two-column grid. */
  base: 1 | 2;
  /** Columns the card takes on the three-column grid (wide screens). */
  wide: 1 | 2 | 3;
}

export function gridSpans(count: number): CardSpan[] {
  return Array.from({ length: count }, (_, i) => {
    const last = i === count - 1;
    const first = i === 0;
    const base: 1 | 2 = last && count % 2 === 1 ? 2 : 1;
    // Three columns: one card left over fills one extra cell (the last one grows by 1), two left over
    // fill two (the first and the last each grow by 1); a lone card takes the whole row.
    const left = count % 3;
    let wide: 1 | 2 | 3 = 1;
    if (count === 1) wide = 3;
    else if (left === 2 && last) wide = 2;
    else if (left === 1 && (first || last)) wide = 2;
    return { base, wide };
  });
}
