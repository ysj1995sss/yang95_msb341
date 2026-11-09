import { Heart } from "lucide-react";
import { useFavorites } from "../hooks";
import type { Route } from "../utils/router";
import { href } from "../utils/router";
import { Logo } from "./Logo";

const links = [
  { label: "Home", to: href.home, page: "home", mobile: false },
  { label: "Explore", to: href.explore, page: "explore", mobile: true },
  { label: "Guess", to: href.guess, page: "guess", mobile: true },
  { label: "About", to: href.about, page: "about", mobile: false },
] as const;

const pill = "inline-flex min-h-11 items-center gap-1.5 rounded-full px-2.5 text-[15px] font-semibold transition-colors sm:px-4";

export function Header({ route }: { route: Route }) {
  const count = useFavorites().length;
  const current = route.page === "play" ? "explore" : route.page === "favorites-play" ? "favorites" : route.page;
  const state = (page: string) => (current === page ? "bg-plum-100 text-plum-800" : "text-muted hover:bg-sand hover:text-ink");
  return (
    <header className="sticky top-0 z-20 border-b border-plum-100/70 bg-cream/85 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-2 px-3 sm:gap-4 sm:px-6">
        <a href={href.home} aria-label="Closer home" className="rounded-2xl">
          <Logo />
        </a>
        <nav aria-label="Main">
          <ul className="flex items-center gap-0.5 sm:gap-1">
            {links.map((link) => (
              <li key={link.page} className={link.mobile ? "" : "hidden sm:block"}>
                <a href={link.to} aria-current={current === link.page ? "page" : undefined} className={`${pill} ${state(link.page)}`}>
                  {link.label}
                </a>
              </li>
            ))}
            <li>
              <a href={href.favorites} aria-current={current === "favorites" ? "page" : undefined}
                aria-label={`Favorites, ${count} saved`} className={`${pill} ${state("favorites")}`}>
                <Heart aria-hidden className="size-4" fill={count ? "currentColor" : "none"} />
                <span className="hidden sm:inline">Favorites</span>
                <span aria-hidden className="min-w-5 rounded-full bg-coral-100 px-1.5 text-center text-xs font-bold text-coral-700">{count}</span>
              </a>
            </li>
          </ul>
        </nav>
      </div>
    </header>
  );
}
