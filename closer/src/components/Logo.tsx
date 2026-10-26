import { Heart } from "lucide-react";

export function Logo({ light = false }: { light?: boolean }) {
  return (
    <span className="inline-flex items-center gap-2">
      <span aria-hidden className="inline-flex size-9 items-center justify-center rounded-2xl bg-gradient-to-br from-plum-600 to-coral-500 text-cream shadow-sm">
        <Heart className="size-5" fill="currentColor" strokeWidth={0} />
      </span>
      <span className={`text-xl font-extrabold tracking-tight ${light ? "text-cream" : "text-ink"}`}>Closer</span>
    </span>
  );
}
