import { Compass, Gamepad2, House, Library, type LucideIcon } from "lucide-react";
import type { Route } from "../utils/router";
import { showsTabBar, tabFor, tabs, type TabId } from "../utils/tabbar";

const icons: Record<TabId, LucideIcon> = { home: House, explore: Compass, games: Gamepad2, library: Library };

/** The phone's way around: Home, Explore, Games and Library fixed to the bottom of the screen, within
 *  thumb's reach. Phones only, and left out while a round or a game is being played. */
export function TabBar({ route }: { route: Route }) {
  if (!showsTabBar(route)) return null;
  const current = tabFor(route);
  return (
    <nav aria-label="Main" className="fixed inset-x-0 bottom-0 z-20 border-t border-plum-100 bg-page/95 pb-[env(safe-area-inset-bottom)] backdrop-blur sm:hidden">
      <ul className="mx-auto grid max-w-md grid-cols-4">
        {tabs.map((tab) => {
          const Icon = icons[tab.id];
          const active = current === tab.id;
          return (
            <li key={tab.id}>
              <a href={tab.to} aria-current={active ? "page" : undefined}
                className={`flex min-h-[var(--tab-bar-height)] flex-col items-center justify-center gap-1 text-xs font-bold transition-colors ${active ? "text-plum-700 dark:text-onplum-soft" : "text-muted"}`}>
                <span className={`inline-flex h-8 w-14 items-center justify-center rounded-full transition-colors ${active ? "bg-plum-100" : ""}`}>
                  <Icon aria-hidden className="size-5" />
                </span>
                {tab.label}
              </a>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
