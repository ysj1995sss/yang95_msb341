# Sprint 3 Review

**Window:** 14 October to 27 October (plan file first commit to now). The reviewed work is the Closer work from 25 October on.
**Sessions reviewed:** 6 across 1 project folder (listed by the scanner under two names). 1 session excluded at your request (a presentation session on 26 October).

## When you worked

Most of the Closer work happened in one push on 25 and 26 October, with a shorter session on 27 October. The Job Copilot sessions from 14 to 24 October are not part of this review.

## Where you got stuck

1. **Getting the site online (25 to 27 October).** The first Vercel import read the `main` branch, which doesn't have the Closer folder. The build then ran from the repository root instead of the `closer` folder, and failed with "vite: command not found". Vercel also asked for a configuration file it didn't need. It ended when the production branch and root directory were set, and the site went live. The address still asked for a Vercel sign-in until deployment protection was switched off.
2. **Which setting to change.** Several screens in Vercel's settings were unclear, and each needed a screenshot and a step-by-step answer before the next click.
3. **Committing and pushing.** A commit was started with a mistyped push command and was re-run.

## What took the most time

By prompt volume, the largest share went to getting the site online, including the Vercel settings. The next largest was building Closer itself: the category pages, question rounds, trivia and the daily question, with the layout checked on desktop and phone. Smaller parts were the Sprint 3 plan change and the review.

## Axis

**Application Architecture.** Most of the work was code, tests and deployment: the Closer data and logic, the automated checks, and the Vercel setup.

## Against your plan

**Goal was:** A simple, working website prototype of Closer: a homepage, 10 question categories, and a way to select a category and answer or skip questions. A basic version people can try by 28 October.

**Done looks like:** A working Closer website with a homepage, 10 categories and at least 10 questions per category. A tester can open the site, select a category, answer or skip each question, and move on with Next, without errors.

**Result, plainly:**
- **Met:** the homepage, the 10 categories, 12 questions in each (120 in all), selecting a category, answering or skipping, moving on with Next, and no console errors. All of these were checked in a browser on desktop and phone, and the automated checks pass.
- **Met:** a tester outside the project opened the live site, picked a category, answered or skipped questions, moved on with Next, and reported no errors. They used a computer. The owner has also used it. The phone check is the owner's only.
- **Beyond the goal:** the trivia round with scoring, the daily question, and the deployment setup. These weren't required.
