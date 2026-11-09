import { useSyncExternalStore } from "react";
import { favorites } from "./utils/storage";

/** The hearted question ids, re-rendering whenever one is added or removed. */
export function useFavorites(): readonly string[] {
  return useSyncExternalStore(favorites.subscribe, favorites.get);
}
