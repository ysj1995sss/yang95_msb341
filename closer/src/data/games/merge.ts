/** Joins card lists into one, keeping the first of any two cards that say the same thing (ignoring capitals and spacing). */
export function mergeUnique<T>(key: (item: T) => string, ...lists: readonly (readonly T[])[]): T[] {
  const seen = new Set<string>();
  const merged: T[] = [];
  for (const item of lists.flat()) {
    const id = key(item).toLowerCase().trim();
    if (seen.has(id)) continue;
    seen.add(id);
    merged.push(item);
  }
  return merged;
}
