import { Suspense, useEffect, useRef } from "react";
import { Footer } from "./components/Footer";
import { Header } from "./components/Header";
import { InstallCard } from "./components/InstallCard";
import { TabBar } from "./components/TabBar";
import { Tour } from "./components/Tour";
import { UpdateNotice } from "./components/UpdateNotice";
import { About } from "./pages/About";
import { DebateNight } from "./pages/DebateNight";
import { Explore } from "./pages/Explore";
import { Favorites, FavoritesPlay } from "./pages/Favorites";
import { Games } from "./pages/Games";
import { gameScreens } from "./pages/gameplay";
import { GuessMyAnswer } from "./pages/GuessMyAnswer";
import { Home } from "./pages/Home";
import { Library } from "./pages/Library";
import { MinePlay, MyQuestions } from "./pages/MyQuestions";
import { PackPlay, Packs } from "./pages/Packs";
import { QuestionExperience } from "./pages/QuestionExperience";
import { Surprise } from "./pages/Surprise";
import { href, useRoute, type Route } from "./utils/router";
import { installCardFitsPage } from "./utils/installCard";
import { currentArrival, restoreScroll, stampEntry } from "./utils/navigation";
import { showsTabBar } from "./utils/tabbar";

/** What identifies a page for "scroll to top and focus the heading": a new key is a new page. */
function pageKey(route: Route): string {
  switch (route.page) {
    case "play": return `play-${route.categoryId}`;
    case "favorites-play": return `fav-${route.categoryId}`;
    case "pack": return `pack-${route.packId}`;
    case "game": return `game-${route.gameId}`;
    default: return route.page;
  }
}

/** Focuses the page's heading. A game screen loads on demand, so if the heading is not there yet,
 *  wait for it for a moment. Returns a function that stops waiting. */
function focusHeadingWhenReady(): () => void {
  const focus = () => {
    const heading = document.querySelector<HTMLElement>("main h1");
    heading?.focus({ preventScroll: true });
    return heading !== null;
  };
  const main = document.getElementById("main");
  if (focus() || !main) return () => undefined;
  const watcher = new MutationObserver(() => { if (focus()) watcher.disconnect(); });
  watcher.observe(main, { childList: true, subtree: true });
  const giveUp = window.setTimeout(() => watcher.disconnect(), 5000);
  return () => { watcher.disconnect(); window.clearTimeout(giveUp); };
}

function NotFound() {
  return (
    <div className="mx-auto max-w-3xl px-4 pt-16 sm:px-6">
      <h1 tabIndex={-1} className="text-3xl font-extrabold">Page not found</h1>
      <p className="mt-3 text-muted">This link doesn't lead anywhere in Closer.</p>
      <a href={href.home} className="mt-6 inline-flex min-h-12 items-center rounded-full bg-plum-600 px-6 font-bold text-white">Go to Home</a>
    </div>
  );
}

/** One game's screen, keyed so moving from one game to another starts fresh. */
function GameScreen({ gameId }: { gameId: string }) {
  const Screen = gameScreens[gameId];
  if (!Screen) return <NotFound />;
  return (
    <Suspense fallback={<p role="status" className="mx-auto max-w-3xl px-4 pt-16 text-muted sm:px-6">Loading the game…</p>}>
      <Screen key={gameId} />
    </Suspense>
  );
}

export default function App() {
  const route = useRoute();
  const key = pageKey(route);
  const tabBar = showsTabBar(route);

  // A page opened fresh starts at the top; going back to one returns to where it was scrolled to.
  // Either way focus goes to the heading for keyboard and screen-reader users.
  // On the very first page the browser starts at the top, so only a reload needs its place restored.
  const firstPage = useRef(true);
  useEffect(() => {
    stampEntry();
    const arrival = currentArrival();
    const back = arrival.kind === "revisit";
    if (firstPage.current) {
      firstPage.current = false;
      return back && arrival.scrollY > 0 ? restoreScroll(arrival.scrollY) : undefined;
    }
    // A dialog (the first-launch tour) that is open keeps focus.
    if (document.querySelector('[role="dialog"][aria-modal="true"]')) return;
    const stopScroll = back ? restoreScroll(arrival.scrollY) : (window.scrollTo({ top: 0, behavior: "instant" }), () => undefined);
    const stopFocus = focusHeadingWhenReady();
    return () => { stopScroll(); stopFocus(); };
  }, [key]);

  return (
    <div className={`flex min-h-dvh flex-col ${tabBar ? "pb-[calc(var(--tab-bar-height)+env(safe-area-inset-bottom))] sm:pb-[env(safe-area-inset-bottom)]" : "pb-[env(safe-area-inset-bottom)]"}`}>
      <a href="#main" onClick={(e) => { e.preventDefault(); document.getElementById("main")?.focus(); }}
        className="sr-only z-50 rounded-full bg-plum-700 px-4 py-2 font-bold text-white focus:not-sr-only focus:fixed focus:left-4 focus:top-3">
        Skip to content
      </a>
      <Header route={route} />
      <main id="main" tabIndex={-1} className="flex-1 outline-none">
        {installCardFitsPage(route) && <InstallCard />}
        {route.page === "home" && <Home />}
        {route.page === "explore" && <Explore />}
        {route.page === "about" && <About />}
        {route.page === "play" && <QuestionExperience key={route.categoryId} categoryId={route.categoryId} />}
        {route.page === "favorites" && <Favorites />}
        {route.page === "favorites-play" && <FavoritesPlay key={route.categoryId ?? "all"} categoryId={route.categoryId} />}
        {route.page === "games" && <Games />}
        {route.page === "game" && <GameScreen gameId={route.gameId} />}
        {route.page === "library" && <Library />}
        {route.page === "guess" && <GuessMyAnswer />}
        {route.page === "debate" && <DebateNight />}
        {route.page === "surprise" && <Surprise />}
        {route.page === "packs" && <Packs />}
        {route.page === "pack" && <PackPlay key={route.packId} packId={route.packId} />}
        {route.page === "mine" && <MyQuestions />}
        {route.page === "mine-play" && <MinePlay />}
        {route.page === "not-found" && <NotFound />}
      </main>
      <Footer />
      <TabBar route={route} />
      <UpdateNotice aboveTabBar={tabBar} />
      <Tour onHome={route.page === "home"} />
    </div>
  );
}
