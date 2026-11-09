# Closer

**Every connection starts with a question.**

Closer is a free app of questions and games for couples, friends, families and teams: pick one of
ten experiences, choose how deep to go, then read each question out loud, talk it over, skip it or
move on. There is nothing to type. It has no backend, no accounts and no paid services: all
questions live in the code, and the only things kept are a person's favorites and play progress,
in their own browser (localStorage / sessionStorage). It can be installed to a phone or computer
and opens without a connection once it has been visited.

## What's in it (Sprint 4)

- **500 questions:** ten experiences with exactly 50 questions each.
  - Love & Relationships, Deep Connections, Party & Games, Debate & Opinions, Family & Memories,
    Icebreakers & Team Building, Would You Rather & Dilemmas, Imagination & Creativity,
    Storytelling Challenges;
  - Trivia & Brain Battles: multiple choice with four options, one answer and an explanation.
  Ids are `<category>-<position>` (for example `love-7`); the first 12 in each category kept the
  ids and wording they had in Sprint 3.
- **Four depth levels** above every question card, switchable at any time:
  - conversation experiences: 1 Fun & Light, 2 Meaningful, 3 Deep, 4 Bold (always optional);
  - trivia: 1 Easy, 2 Medium, 3 Hard, 4 Expert;
  - **Mix** shows every level. Each level has 11 to 14 questions per category. The card shows its
    level, and the selector shows how many are left at each.
- **No repeats, real shuffle:** a Fisher–Yates shuffle once per round. A question that has been
  shown (answered, skipped, or swapped away by changing depth) is never shown again. When a level
  or the whole set is used up you get a completion screen: switch level, or start over with a
  fresh shuffle. Progress survives a refresh while the tab stays open.
- **Favorites:** a heart on every card. **My Favorites** (`#/favorites`) groups saved questions by
  category, lets you play them again (all, or one category), and has an empty state. Saved in
  localStorage; no duplicates.
- **Trivia scoring:** one question at a time, choose then submit. You see right or wrong, the
  correct option highlighted, and an explanation. A question scores once. A quiz is 10 questions,
  then results: answered, correct, incorrect, percentage, play again, return to categories.
- **Guess My Answer** (`#/guess`): a two-player pass-and-play game on one device. One player
  secretly picks one of four answers, the device is handed over, the other guesses; a match scores
  a point, and roles swap each round. 60 questions in six themes, 4 to 10 rounds, final score and
  replay. Nothing is graded from free text.
- **Conversation, not a form:** the question cards have no text box. A card has Skip and Next; a
  finished round says how many you "talked through" and how many you skipped. (Feedback from a
  tester: the text box got in the way of a spoken conversation. Accounts to save answers were
  considered and left for later.)
- **Installable app:** a web app manifest, home-screen icons and a service worker. Add it to a
  home screen (the About page has the steps), and after one visit it opens offline, including
  the question library and the page's font. Every path is relative, so it also works from a
  subfolder such as GitHub Pages.
- **Question of the Day**, **Home**, **Explore**, **About**: the home page opens with a plain line
  saying what Closer is; Home and Explore point to Guess My Answer; the header has a Favorites
  link with a count.
- **Pages:** `#/`, `#/explore`, `#/about`, `#/play/<category>`, `#/favorites`,
  `#/favorites/play[/<category>]`, `#/guess`. Pages live after the "#", so links, refresh and the
  Back button work on any static host with no server setup.

## Run it locally

You need Node.js 20 or newer.

```bash
cd closer
npm install
npm run dev
```

Then open http://localhost:5173.

On this project's own computer, npm isn't on PATH. It lives in `D:\Yang\Software\cursor\NodeJs`.

## Check it

```bash
npm test
```

This runs 54 automated checks:

- **Content (`src/data.test.ts`):** ten categories; exactly 500 questions and 50 per category;
  unique, stable ids and preserved Sprint 3 ids and wording; clean writing; no exact duplicates
  and no near-duplicates; varied sentence shapes; 11 to 14 questions per depth level in every
  category; every trivia question has four distinct options, a valid answer, an explanation and a
  balanced answer position; Guess My Answer questions are complete.
- **Logic (`src/utils.test.ts`):** the shuffle is a fair Fisher–Yates; a session never repeats a
  question, counts skips as seen, keeps its place when depth changes, reports progress, finishes
  and restarts; a trivia question scores once; favorites toggle, never duplicate, persist and
  survive blocked storage; talked-through versus skipped; a depth change is never counted as a
  skip; the quiz headline and score use the same base; Guess My Answer phases, secrecy, scoring
  once, alternating roles and final winner; page addresses.
- **Installable app (`src/pwa.test.ts`):** the manifest, icons, page links and service worker.

```bash
npm run build
```

This type-checks the code and builds the site into `dist/`.

### Test the main flows by hand

1. **Depth:** open any conversation experience. Press each level in turn; the card's label and the
   "n left" counts change and no question appears twice.
2. **Complete a set:** choose one level and press Skip until the completion screen. Pick another
   level, or "Start over".
3. **Favorites:** press the heart, reload (it stays), open My Favorites, play it again, then
   remove it and see the empty state.
4. **Trivia:** pick an answer and submit. After 10 questions you see answered, correct, incorrect
   and the percentage.
5. **Guess My Answer:** start a 4-round game. The secret answer is hidden on the hand-off screen.
6. **Phone:** try all of the above at phone width. Nothing should scroll sideways.
7. **Install and offline:** run `npm run build` then `npm run preview`, open the preview address in
   Chrome, reload once, and install it from the address bar. Turn the network off (DevTools,
   Network, Offline) and reload: the app still opens and plays. The service worker is off in
   `npm run dev` on purpose.

## Deploy it

The build is a static site (`dist/`). Its asset paths are relative, so it works at a site's root or
in a subfolder. The existing deployment setup is unchanged.

- **Vercel:**
  1. New Project, then import this repository.
  2. Set Root Directory to `closer`.
  3. Framework: Vite. Build command: `npm run build`. Output: `dist`.
  4. Pushing to the production branch redeploys automatically.
- **Netlify:**
  1. Add new site, then import from Git.
  2. Base directory: `closer`. Build command: `npm run build`. Publish directory: `closer/dist`.
- **GitHub Pages:**
  1. Run `npm run build`.
  2. Publish the contents of `dist/`, for example on a `gh-pages` branch or with the "Deploy static
     content to Pages" GitHub Action pointed at `closer/dist`.

## Notes on the content

- Trivia answers were checked against reliable references while writing; a human read-through
  before a wide launch is still a good idea.
- The questions were written for this project, reviewed for duplicates by automated checks and a
  read of the closest pairs.

## Ideas for the next sprint

- **Real testers:** watch 3–5 people use it and note where they hesitate.
- **More questions:** extend each experience beyond 50, and add more Guess My Answer themes.
- **Self-host the font:** the page's typeface still comes from Google Fonts. Bundling it removes
  a third-party request and makes the very first offline visit match.
- **Journal mode:** only if testers ask for it. It would need accounts and a backend.
- **App stores:** the installable web app can later be wrapped for the Apple and Google stores.
