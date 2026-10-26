import type { Route } from "../utils/router";
import { href } from "../utils/router";
import { Logo } from "./Logo";

const links = [
  { label: "Home", to: href.home, page: "home" },
  { label: "Explore", to: href.explore, page: "explore" },
  { label: "About", to: href.about, page: "about" },
] as const;

export function Header({ route }: { route: Route }) {
  const current = route.page === "play" ? "explore" : route.page;
  return (
    <header className="sticky top-0 z-20 border-b border-plum-100/70 bg-cream/85 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-4 px-4 sm:px-6">
        <a href={href.home} aria-label="Closer home" className="rounded-2xl">
          <Logo />
        </a>
        <nav aria-label="Main">
          <ul className="flex items-center gap-1">
            {links.map((link) => (
              <li key={link.page}>
                <a
                  href={link.to}
                  aria-current={current === link.page ? "page" : undefined}
                  className={`inline-flex min-h-11 items-center rounded-full px-3 text-[15px] font-semibold transition-colors sm:px-4 ${
                    current === link.page ? "bg-plum-100 text-plum-800" : "text-muted hover:bg-sand hover:text-ink"
                  }`}
                >
                  {link.label}
                </a>
              </li>
            ))}
          </ul>
        </nav>
      </div>
    </header>
  );
}
