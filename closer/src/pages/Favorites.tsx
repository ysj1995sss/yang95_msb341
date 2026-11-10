import { ArrowRight, Heart, Play } from "lucide-react";
import { useState } from "react";
import { CategoryIcon } from "../components/CategoryIcon";
import { DepthMeter } from "../components/DepthSelector";
import { FavoriteButton } from "../components/FavoriteButton";
import { SessionView } from "../components/SessionView";
import { primary, secondary } from "../components/ui";
import { categories, categoryById } from "../data/categories";
import { levelsFor } from "../data/depth";
import { findQuestion, sourceLabel } from "../data/lookup";
import { useFavorites } from "../hooks";
import type { Question } from "../types";
import { favorites } from "../utils/storage";
import { href } from "../utils/router";

/** Ids that still exist in the library, as questions (a saved id from an older library is dropped). */
function favoriteQuestions(ids: readonly string[]): Question[] {
  return ids.map(findQuestion).filter((q): q is Question => !!q);
}

function EmptyState() {
  return (
    <div className="mt-10 rounded-[2rem] border border-dashed border-plum-200 bg-surface/70 p-8 text-center sm:p-12">
      <span aria-hidden className="mx-auto inline-flex size-16 items-center justify-center rounded-full bg-coral-100 text-coral-700">
        <Heart className="size-8" />
      </span>
      <h2 className="mt-5 text-2xl font-extrabold">No favorites yet</h2>
      <p className="mx-auto mt-2 max-w-md text-muted">
        Tap the heart on any question to keep it here. Your favorites stay on this device so you can come back to them.
      </p>
      <a href={href.explore} className={`${primary} mt-6`}>Find questions to save <ArrowRight aria-hidden className="size-5" /></a>
    </div>
  );
}

/** My Favorites: saved questions grouped by category, with a way to play them again. */
export function Favorites() {
  const ids = useFavorites();
  const saved = favoriteQuestions(ids);

  return (
    <div className="mx-auto max-w-3xl px-4 pt-12 sm:px-6">
      <h1 tabIndex={-1} className="text-4xl font-extrabold tracking-tight sm:text-5xl">My Favorites</h1>
      <p className="mt-3 max-w-2xl text-lg text-muted">
        {saved.length
          ? `${saved.length} saved ${saved.length === 1 ? "question" : "questions"}, kept on this device.`
          : "The questions you love, saved in one place."}
      </p>

      {saved.length === 0 ? (
        <EmptyState />
      ) : (
        <>
          <div className="mt-6 flex flex-wrap gap-3">
            <a href={href.playFavorites()} className={primary}><Play aria-hidden className="size-5" /> Play all favorites</a>
            <button type="button" className={secondary}
              onClick={() => { if (window.confirm("Remove all favorites from this device?")) [...ids].forEach((id) => favorites.toggle(id)); }}>
              Clear all
            </button>
          </div>
          <div className="mt-10 space-y-10">
            {categories.map((category) => {
              const items = saved.filter((q) => q.categoryId === category.id);
              if (items.length === 0) return null;
              const names = levelsFor(category.id);
              return (
                <section key={category.id} aria-labelledby={`fav-${category.id}`}>
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div className="flex items-center gap-3">
                      <CategoryIcon category={categoryById(category.id)!} />
                      <h2 id={`fav-${category.id}`} className="text-xl font-extrabold">
                        {category.name} <span className="text-base font-semibold text-muted">({items.length})</span>
                      </h2>
                    </div>
                    <a href={href.playFavorites(category.id)} className="inline-flex min-h-11 items-center gap-2 rounded-full border-2 border-plum-200 bg-surface px-4 text-sm font-bold text-plum-800 transition hover:border-plum-300 hover:bg-plum-50">
                      <Play aria-hidden className="size-4" /> Play these
                    </a>
                  </div>
                  <ul className="mt-4 space-y-3">
                    {items.map((q) => (
                      <li key={q.id} className="flex items-start justify-between gap-3 rounded-2xl border border-plum-100 bg-surface p-4 pl-5 shadow-sm">
                        <div>
                          <p className="text-[17px] font-bold leading-snug">{q.text}</p>
                          <p className="mt-2 flex items-center gap-2 text-sm font-semibold text-muted">
                            <DepthMeter depth={q.depth} /> {names[q.depth].name}
                          </p>
                        </div>
                        <FavoriteButton questionId={q.id} />
                      </li>
                    ))}
                  </ul>
                </section>
              );
            })}
            {/* Hearts from seasonal packs and from the player's own questions. */}
            {saved.some((q) => q.categoryId === "pack" || q.categoryId === "mine") && (
              <section aria-labelledby="fav-other">
                <h2 id="fav-other" className="text-xl font-extrabold">
                  Packs and my questions <span className="text-base font-semibold text-muted">({saved.filter((q) => q.categoryId === "pack" || q.categoryId === "mine").length})</span>
                </h2>
                <ul className="mt-4 space-y-3">
                  {saved.filter((q) => q.categoryId === "pack" || q.categoryId === "mine").map((q) => (
                    <li key={q.id} className="flex items-start justify-between gap-3 rounded-2xl border border-plum-100 bg-surface p-4 pl-5 shadow-sm">
                      <div>
                        <p className="text-[17px] font-bold leading-snug">{q.text}</p>
                        <p className="mt-2 flex items-center gap-2 text-sm font-semibold text-muted">
                          <DepthMeter depth={q.depth} /> {levelsFor(q.categoryId)[q.depth].name} <span aria-hidden>·</span> {sourceLabel(q)}
                        </p>
                      </div>
                      <FavoriteButton questionId={q.id} />
                    </li>
                  ))}
                </ul>
              </section>
            )}
          </div>
        </>
      )}
    </div>
  );
}

/** Replays saved questions (all of them, or one category's) with the same play screen as the library. */
export function FavoritesPlay({ categoryId }: { categoryId: string | null }) {
  // Fixed when the page opens, so un-hearting a card mid-game doesn't reshuffle the set.
  const [pool] = useState(() =>
    favoriteQuestions(favorites.get()).filter((q) => categoryId === null || q.categoryId === categoryId),
  );
  const category = categoryId ? categoryById(categoryId) ?? null : null;

  if (pool.length === 0) {
    return (
      <div className="mx-auto max-w-3xl px-4 pt-12 sm:px-6">
        <h1 tabIndex={-1} className="text-3xl font-extrabold tracking-tight">Nothing to play yet</h1>
        <EmptyState />
        <a href={href.favorites} className={`${secondary} mt-6`}>Back to favorites</a>
      </div>
    );
  }
  return (
    <SessionView
      category={category}
      heading={category ? `${category.name}: favorites` : "Play your favorites"}
      description={`${pool.length} saved ${pool.length === 1 ? "question" : "questions"}, in a fresh order.`}
      pool={pool}
      backHref={href.favorites}
      backLabel="Back to favorites"
    />
  );
}
