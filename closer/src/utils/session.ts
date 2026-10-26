/** Up to `count` of `ids` in a random order, none twice (a Fisher-Yates shuffle). */
export function sessionOrder(ids: string[], count: number, random: () => number = Math.random): string[] {
  const order = [...ids];
  for (let i = order.length - 1; i > 0; i--) {
    const j = Math.floor(random() * (i + 1));
    [order[i], order[j]] = [order[j], order[i]];
  }
  return order.slice(0, count);
}
