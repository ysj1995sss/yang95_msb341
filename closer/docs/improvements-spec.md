# Closer improvements: decisions from the grilling session

Terms follow `closer/CONTEXT.md`. Built (not yet committed); "As built" notes mark where the build differs from the plan.

## 1. Installed experience
- **Install card:** a dismissible "Install Closer" card for phones, shown after a person starts their first round, on any top-level page (not only Home). It includes the iPhone steps (Safari, then Share, then Add to Home Screen). It is hidden once the app is installed or dismissed; the dismissal is remembered on the device.
  *As built:* "started a round" means at least one question in a round was talked about or skipped; About is left out
  because it already has its own Install Closer section.
- **Safe areas and app feel:** `viewport-fit=cover` and `env(safe-area-inset-*)` padding for the tab bar and footer; no pull-to-refresh bounce in the installed app; no accidental text selection on buttons; tap highlight off.
- **Update notice:** when a new version has been deployed, show "New version available, tap to refresh".
  *As built:* the service worker fetches from the network first, so a fresh load is always current; the
  stale case is an installed app resumed from the background. So each time the page comes back into view
  it re-fetches `index.html` and compares the main script it names with the running one.
- **Not doing:** iPhone splash screens.

## 4. Tab bar (phones only, below the `sm` breakpoint)
- Four tabs: Home, Explore, Games, Library.
- Shown on top-level pages: home, explore, games, library, about, favorites, mine, packs.
- Hidden on play screens: play, guess, debate, surprise, pack, favorites-play, mine-play.
- Phone header: logo and theme toggle only. Desktop header: Home, Explore, Games, Library, About, plus the Favorites heart (links to Favorites).
- Page bottom padding (and the footer) so the tab bar never covers content.

## 5. Card grid
- With an odd number of cards, the last card spans the full row on the 2-column layouts. It must hold for any count, because the audience filter hides cards.
- On wide screens Love spans two columns and Trivia spans two (Love + Deep, then 3 cards, then Imagination + Trivia).

## 6. Library hub
- New route `#/library` with three tinted cards (Favorites, My questions, Seasonal packs) and counts, like the Games hub.
- Existing pages keep their URLs and gain a "Back to library" link.

## 7. Home and Explore
- Home: hero (Start Exploring, Surprise me, install button), Continue card, Question of the Day. The category grid and "More ways to play" leave Home.
- Explore keeps the grid and drops "More ways to play" (Games and Library are in the navigation).

## Done looks like
- Type check, unit tests (router, install, library) and build pass.
- Browser walkthrough passes in iPhone emulation and installed (standalone) mode, light and dark, with no horizontal overflow at 375px and no accessibility violations.
- Shown to the user before any commit or deploy.
