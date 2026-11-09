import { Heart } from "lucide-react";
import { useFavorites } from "../hooks";
import { favorites } from "../utils/storage";

/** The heart on a question card. Pressed means saved to My Favorites. */
export function FavoriteButton({ questionId }: { questionId: string }) {
  const saved = useFavorites().includes(questionId);
  return (
    <button
      type="button"
      aria-pressed={saved}
      aria-label={saved ? "Remove from favorites" : "Save to favorites"}
      onClick={() => favorites.toggle(questionId)}
      className={`inline-flex size-12 shrink-0 cursor-pointer items-center justify-center rounded-full transition ${
        saved ? "bg-coral-100 text-coral-700 hover:bg-coral-200" : "text-muted hover:bg-sand hover:text-coral-700"
      }`}
    >
      <Heart aria-hidden className="size-6" fill={saved ? "currentColor" : "none"} />
    </button>
  );
}
