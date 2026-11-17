import { href } from "../utils/router";
import { Logo } from "./Logo";

const links = [
  { label: "Explore", to: href.explore },
  { label: "Games", to: href.games },
  { label: "Seasonal packs", to: href.packs },
  { label: "My questions", to: href.mine },
  { label: "My Favorites", to: href.favorites },
  { label: "About", to: href.about },
];

export function Footer() {
  return (
    <footer className="mt-16 border-t border-plum-100 bg-surface/60">
      <div className="mx-auto flex max-w-6xl flex-col gap-5 px-4 py-8 sm:px-6 md:flex-row md:items-center md:justify-between">
        <div>
          <Logo />
          <p className="mt-2 text-sm text-muted">Every connection starts with a question.</p>
        </div>
        <nav aria-label="Footer">
          <ul className="flex flex-wrap gap-x-1 gap-y-0.5">
            {links.map((link) => (
              <li key={link.label}>
                <a href={link.to} className="inline-flex min-h-11 items-center rounded-full px-3 text-sm font-semibold text-muted transition-colors hover:bg-plum-50 hover:text-ink">
                  {link.label}
                </a>
              </li>
            ))}
          </ul>
        </nav>
        <p className="max-w-56 text-sm text-muted">Your favorites, questions and progress stay on this device.</p>
      </div>
    </footer>
  );
}
