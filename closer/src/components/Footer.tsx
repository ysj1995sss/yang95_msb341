import { href } from "../utils/router";
import { Logo } from "./Logo";

const links = [
  { label: "Explore", to: href.explore },
  { label: "Guess My Answer", to: href.guess },
  { label: "My Favorites", to: href.favorites },
  { label: "About", to: href.about },
];

export function Footer() {
  return (
    <footer className="mt-20 bg-plum-900 text-plum-100">
      <div className="mx-auto flex max-w-6xl flex-col gap-6 px-4 py-10 sm:px-6 md:flex-row md:items-center md:justify-between">
        <div>
          <Logo light />
          <p className="mt-2 text-sm text-plum-200">Every connection starts with a question.</p>
        </div>
        <nav aria-label="Footer">
          <ul className="flex flex-wrap gap-x-2 gap-y-1">
            {links.map((link) => (
              <li key={link.label}>
                <a href={link.to} className="inline-flex min-h-11 items-center rounded-full px-3 text-sm font-semibold text-plum-100 transition-colors hover:bg-white/10">
                  {link.label}
                </a>
              </li>
            ))}
          </ul>
        </nav>
        <p className="text-sm text-plum-200">Your favorites stay on this device.</p>
      </div>
    </footer>
  );
}
