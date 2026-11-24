import { Heart } from "lucide-react";
import { useFavorites } from "../hooks";
import type { Route } from "../utils/router";
import { href } from "../utils/router";
import { tabFor, tabs } from "../utils/tabbar";
import { Logo } from "./Logo";
import { ThemeToggle } from "./ThemeToggle";

const pill = "inline-flex min-h-11 items-center gap-1.5 rounded-full px-4 text-[15px] font-semibold transition-colors";

/** The top bar. On a phone it is just the logo and the dark-mode switch (the tab bar at the bottom
 *  does the navigating); from tablet width up it carries the links too. */
export function Header({ route }: { route: Route }) {
  const count = useFavorites().length;
  const current: string = tabFor(route) ?? route.page;
  const look = (on: boolean) => (on ? "bg-plum-100 text-plum-800" : "text-muted hover:bg-sand hover:text-ink");
  const links: { page: string; label: string; to: string }[] = [...tabs.map((t) => ({ page: t.id, label: t.label, to: t.to })), { page: "about", label: "Help", to: href.help }];
  return (
    <header className="sticky top-0 z-20 border-b border-plum-100/70 bg-page/85 pt-[env(safe-area-inset-top)] backdrop-blur">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-4 px-4 sm:px-6">
        <a href={href.home} aria-label="Closer home" className="inline-flex min-h-11 items-center rounded-2xl">
          <Logo />
        </a>
        <div className="flex items-center gap-1">
          <nav aria-label="Main" className="hidden sm:block">
            <ul className="flex items-center gap-1">
              {links.map((link) => (
                <li key={link.page}>
                  <a href={link.to} aria-current={current === link.page ? "page" : undefined} className={`${pill} ${look(current === link.page)}`}>
                    {link.label}
                  </a>
                </li>
              ))}
              <li>
                <a href={href.favorites} aria-current={route.page === "favorites" ? "page" : undefined}
                  aria-label={`Favorites, ${count} saved`} className={`${pill} ${look(route.page === "favorites")}`}>
                  <Heart aria-hidden className="size-4" fill={count ? "currentColor" : "none"} />
                  <span className="hidden md:inline">Favorites</span>
                  <span aria-hidden className="min-w-5 rounded-full bg-coral-100 px-1.5 text-center text-xs font-bold text-coral-700">{count}</span>
                </a>
              </li>
            </ul>
          </nav>
          <ThemeToggle />
        </div>
      </div>
    </header>
  );
}
