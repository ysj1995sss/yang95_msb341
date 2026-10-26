import { BookOpen, Brain, Camera, Heart, PartyPopper, Scale, Snowflake, Sparkles, Split, Waves, type LucideIcon } from "lucide-react";
import type { Category } from "../types";

const icons: Record<Category["icon"], LucideIcon> = {
  Heart, Waves, PartyPopper, Scale, Camera, Snowflake, Split, Brain, Sparkles, BookOpen,
};

/** The category's icon on its gradient tile. Decorative: the category name sits beside it. */
export function CategoryIcon({ category, size = "md" }: { category: Category; size?: "md" | "lg" }) {
  const Icon = icons[category.icon];
  const box = size === "lg" ? "size-16 rounded-3xl" : "size-12 rounded-2xl";
  return (
    <span aria-hidden className={`inline-flex shrink-0 items-center justify-center bg-gradient-to-br text-white shadow-md ${box} ${category.gradient}`}>
      <Icon className={size === "lg" ? "size-8" : "size-6"} strokeWidth={2.2} />
    </span>
  );
}
