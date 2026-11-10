import { useEffect, useRef } from "react";
import { Footer } from "./components/Footer";
import { Header } from "./components/Header";
import { Tour } from "./components/Tour";
import { About } from "./pages/About";
import { DebateNight } from "./pages/DebateNight";
import { Explore } from "./pages/Explore";
import { Favorites, FavoritesPlay } from "./pages/Favorites";
import { GuessMyAnswer } from "./pages/GuessMyAnswer";
import { Home } from "./pages/Home";
import { MinePlay, MyQuestions } from "./pages/MyQuestions";
import { PackPlay, Packs } from "./pages/Packs";
import { QuestionExperience } from "./pages/QuestionExperience";
import { Surprise } from "./pages/Surprise";
import { href, useRoute, type Route } from "./utils/router";

/** What identifies a page for "scroll to top and focus the heading": a new key is a new page. */
function pageKey(route: Route): string {
  switch (route.page) {
    case "play": return `play-${route.categoryId}`;
    case "favorites-play": return `fav-${route.categoryId}`;
    case "pack": return `pack-${route.packId}`;
    default: return route.page;
  }
}

export default function App() {
  const route = useRoute();
  const key = pageKey(route);

  // A new page starts at the top, with focus on its heading for keyboard and screen-reader users.
  // Not on the first visit: there the browser already starts at the top of the page.
  const firstPage = useRef(true);
  useEffect(() => {
    if (firstPage.current) { firstPage.current = false; return; }
    // A dialog (the first-launch tour) that is open keeps focus.
    if (document.querySelector('[role="dialog"][aria-modal="true"]')) return;
    window.scrollTo({ top: 0 });
    document.querySelector<HTMLElement>("main h1")?.focus({ preventScroll: true });
  }, [key]);

  return (
    <div className="flex min-h-dvh flex-col">
      <a href="#main" onClick={(e) => { e.preventDefault(); document.getElementById("main")?.focus(); }}
        className="sr-only z-50 rounded-full bg-plum-700 px-4 py-2 font-bold text-white focus:not-sr-only focus:fixed focus:left-4 focus:top-3">
        Skip to content
      </a>
      <Header route={route} />
      <main id="main" tabIndex={-1} className="flex-1 outline-none">
        {route.page === "home" && <Home />}
        {route.page === "explore" && <Explore />}
        {route.page === "about" && <About />}
        {route.page === "play" && <QuestionExperience key={route.categoryId} categoryId={route.categoryId} />}
        {route.page === "favorites" && <Favorites />}
        {route.page === "favorites-play" && <FavoritesPlay key={route.categoryId ?? "all"} categoryId={route.categoryId} />}
        {route.page === "guess" && <GuessMyAnswer />}
        {route.page === "debate" && <DebateNight />}
        {route.page === "surprise" && <Surprise />}
        {route.page === "packs" && <Packs />}
        {route.page === "pack" && <PackPlay key={route.packId} packId={route.packId} />}
        {route.page === "mine" && <MyQuestions />}
        {route.page === "mine-play" && <MinePlay />}
        {route.page === "not-found" && (
          <div className="mx-auto max-w-3xl px-4 pt-16 sm:px-6">
            <h1 tabIndex={-1} className="text-3xl font-extrabold">Page not found</h1>
            <p className="mt-3 text-muted">This link doesn't lead anywhere in Closer.</p>
            <a href={href.home} className="mt-6 inline-flex min-h-12 items-center rounded-full bg-plum-600 px-6 font-bold text-white">Go to Home</a>
          </div>
        )}
      </main>
      <Footer />
      <Tour onHome={route.page === "home"} />
    </div>
  );
}
