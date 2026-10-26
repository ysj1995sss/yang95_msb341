import { useEffect, useState } from "react";

// Pages live in the address after "#" (#/explore, #/play/love), so links, the Back button and
// refresh all work on any static host, GitHub Pages included, with no server setup.

export type Route =
  | { page: "home" }
  | { page: "explore" }
  | { page: "about" }
  | { page: "play"; categoryId: string }
  | { page: "not-found" };

export function parseRoute(hash: string): Route {
  const path = hash.replace(/^#/, "").replace(/\/+$/, "") || "/";
  if (path === "/" || path === "") return { page: "home" };
  if (path === "/explore") return { page: "explore" };
  if (path === "/about") return { page: "about" };
  const play = path.match(/^\/play\/([a-z-]+)$/);
  if (play) return { page: "play", categoryId: play[1] };
  return { page: "not-found" };
}

export function useRoute(): Route {
  const [route, setRoute] = useState<Route>(() => parseRoute(window.location.hash));
  useEffect(() => {
    const onChange = () => setRoute(parseRoute(window.location.hash));
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);
  return route;
}

export const href = {
  home: "#/",
  explore: "#/explore",
  about: "#/about",
  play: (categoryId: string) => `#/play/${categoryId}`,
};
