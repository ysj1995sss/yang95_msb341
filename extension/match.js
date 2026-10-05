// Does a frame's address fall under one of the manifest's host patterns (like
// "https://*.myworkdayjobs.com/*")? A "*" never crosses a "/", so a pattern can't match an
// address that only mentions the site later on. Used by popup.js; tested in apps/web/e2e.
function matchesHostPattern(pattern, url) {
  const escaped = pattern.split("*").map((part) => part.replace(/[.?+^$()[\]{}|\\/]/g, "\\$&"));
  return new RegExp(`^${escaped.join("[^/]*")}`).test(url);
}
