# Closer

**Every connection starts with a question.**

Closer is a question-based social experience: pick one of ten experiences, then answer, skip or
move to the next question. This folder is the first website prototype (Sprint 3). It has no
backend, no accounts and no paid services: all questions live in the code, and anything a person
writes is saved only in their own browser (localStorage).

## What's in it

- **Home:** the brand and tagline, a Question of the Day, all ten experiences, and how it works.
- **Ten experiences, 12 questions each (120 in all):**
  - Love & Relationships, Deep Connections, Party & Games, Debate & Opinions, Family & Memories,
    Icebreakers & Team Building, Would You Rather, Imagination & Creativity, Storytelling
    Challenges;
  - Trivia & Brain Battles: multiple choice, with feedback, an explanation and a score.
- **A round:** 10 of a category's questions in a random order, none repeated. For each one:
  - **open questions:** answer (optional), save, skip, or go to the next one;
  - **trivia:** pick an answer, submit, see if it was right and why.
  A results screen closes the round.
- **Question of the Day:** the same question all day, by the local date, with an optional saved
  answer.
- **Pages:** `#/` (Home), `#/explore`, `#/about`, `#/play/<category>`. Pages live after the "#", so links,
  refresh and the Back button work on any static host with no server setup.

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

This runs 14 checks on the content and logic:
- ten experiences, at least 10 questions each and 100 in all;
- no question repeated anywhere;
- every trivia question has four options, one answer and an explanation;
- the daily question stays the same all day;
- a round never repeats a question;
- saving never breaks the page.

```bash
npm run build
```

This type-checks the code and builds the site into `dist/`.

### Test the main flows by hand

1. **Home:** check the headline, the tagline and the ten experience cards.
2. **Question of the Day:** click Reveal, write an answer, and save it. Reload the page; the answer is still there.
3. **An open round:** open any experience except Trivia. Answer and save one question, skip one, and press
   Next question until the results screen. It counts what you answered and skipped. Play another
   round starts again in a new order.
4. **Trivia:** pick an answer and submit. It shows right or wrong, the correct answer and an
   explanation. After 10 questions you see your score.
5. **Phone:** try all of the above at phone width. Nothing should scroll sideways.

## Deploy it

The build is a static site (`dist/`). Its asset paths are relative, so it works at a site's root or
in a subfolder.

- **Vercel:**
  1. New Project, then import this repository.
  2. Set Root Directory to `closer`.
  3. Framework: Vite. Build command: `npm run build`. Output: `dist`.
- **Netlify:**
  1. Add new site, then import from Git.
  2. Base directory: `closer`. Build command: `npm run build`. Publish directory: `closer/dist`.
- **GitHub Pages:**
  1. Run `npm run build`.
  2. Publish the contents of `dist/`, for example on a `gh-pages` branch or with the "Deploy static
     content to Pages" GitHub Action pointed at `closer/dist`.

## Ideas for the next sprint

- **Real testers:** watch 3–5 people use it and note where they hesitate.
- **Play together:** pass-the-phone mode, or a shared room code for groups.
- **Favorites and history:** keep questions people liked, and see past answers.
- **More questions:** add depth levels (light / deeper) within each experience.
- **Mobile app:** the same experience packaged for phones (e.g., as an installable web app first).
