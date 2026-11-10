// Closer's service worker: after one visit the app opens without a connection.
// Same-origin pages and files (and the Google Fonts files) are fetched from the network first, so
// a new deploy shows up straight away, and kept in a cache; when the network is gone, the cached
// copy is used.
// Paths are relative, so this works at a site's root or in a subfolder (GitHub Pages).

const CACHE = "closer-v1";
const SHELL = ["./", "./index.html", "./manifest.webmanifest", "./favicon.svg", "./icons/icon-192.png"];

self.addEventListener("install", (event) => {
  event.waitUntil(
    (async () => {
      const cache = await caches.open(CACHE);
      await cache.addAll(SHELL);
      // The built page names its hashed script and stylesheet files; keep those too so the very
      // first visit can already be reopened offline.
      const html = await (await fetch("./index.html", { cache: "no-store" })).text();
      const assets = [...html.matchAll(/(?:src|href)="(\.\/assets\/[^"]+)"/g)].map((m) => m[1]);
      await Promise.all(assets.map((url) => cache.add(url).catch(() => undefined)));
      await self.skipWaiting();
    })(),
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    (async () => {
      const names = await caches.keys();
      await Promise.all(names.filter((name) => name !== CACHE).map((name) => caches.delete(name)));
      await self.clients.claim();
    })(),
  );
});

// The page's typeface comes from Google Fonts; keeping it makes the offline app look the same.
const FONT_HOSTS = ["fonts.googleapis.com", "fonts.gstatic.com"];

self.addEventListener("fetch", (event) => {
  const { request } = event;
  const url = new URL(request.url);
  if (request.method !== "GET" || (url.origin !== self.location.origin && !FONT_HOSTS.includes(url.hostname))) return;

  event.respondWith(
    (async () => {
      const cache = await caches.open(CACHE);
      try {
        const response = await fetch(request);
        // Cross-origin font responses are "opaque": they can be stored and replayed, just not read.
        if (response.ok || response.type === "opaque") cache.put(request, response.clone());
        return response;
      } catch {
        const cached = await cache.match(request);
        if (cached) return cached;
        if (request.mode === "navigate") return (await cache.match("./index.html")) ?? (await cache.match("./"));
        return Response.error();
      }
    })(),
  );
});
