import { Cake, Ghost, Heart, Leaf, Snowflake, Sparkles, Sun, type LucideIcon } from "lucide-react";
import type { Pack, PackIconName } from "../types";

const icons: Record<PackIconName, LucideIcon> = { Heart, Sparkles, Sun, Ghost, Leaf, Snowflake, Cake };

/** A pack's icon on its gradient tile, like a category's. */
export function PackIcon({ pack, size = "md" }: { pack: Pack; size?: "md" | "lg" }) {
  const Icon = icons[pack.icon];
  const box = size === "lg" ? "size-16 rounded-3xl" : "size-12 rounded-2xl";
  return (
    <span aria-hidden className={`inline-flex shrink-0 items-center justify-center bg-gradient-to-br ${pack.gradient} text-white shadow-md ${box}`}>
      <Icon className={size === "lg" ? "size-8" : "size-6"} />
    </span>
  );
}
