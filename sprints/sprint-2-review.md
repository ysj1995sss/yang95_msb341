# Sprint 2 Review

**Window:** 2026-09-22 to 2026-10-13 (plan committed 2026-09-22 08:18)
**Sessions reviewed:** 14 across 2 projects (1 session excluded at your request)

Session counts come from the two folders you confirmed: the product repo (`yang95_msb341`) and the
folder this chat runs from (`Claude`). Some sessions began before the window, so the per-day
counts below include a few prompts from 17 and 21 September; those are not counted in the window
totals. Git records 259 commits to the product repo since 22 September.

## When you worked

Active on 17 of the 22 days in the window. The work came in bursts rather than a steady pace:
- **Heaviest:** 28–29 September, 4–5 October, and 13 October. Together these account for most of
  the window's prompts.
- **Quiet stretches:** 2 October, 8 October and 10 October.
- **Shape:** bunched, with a long push at the end (13 October alone has 136 prompts, more than any
  earlier day).

## Where you got stuck

1. **Resume quality after tailoring (22 September, 24 September, 6 October).** Your own resume came
   back "not up to standard" more than once, and you pasted an external prompt to fix it. Ended
   with validation rules and a later review screen (decisions 032–044), but the quality question
   stayed open.
2. **Model provider errors (28 September).** Repeated rate-limit and upstream errors from the
   providers the app was using, followed by repeated "Running the app again". Ended by moving to
   a different model setup.
3. **Retry loops (repeated "Try again" on 24 and 28 September, 30 September, 6 and 7 October).**
   Each retry was a fresh attempt at a failing run. Ended when the cause was found, or the failure
   was recorded as a known gap.
4. **Word-to-PDF and page-length failures (5 October, 12–13 October).** Diagnosed with the debugging
   skill on 5 October; the same family of failures came back on the live site on 13 October, this
   time on the free backend. Ended with a dedicated Word-conversion fix (spec 020) and a fitting
   change, but the live Word path is still unverified.
5. **Online deployment (12–13 October).** Most of the final day went to deploying the backend and
   website, one error at a time: a missing secret, an empty key, a retired model name, and a
   backend that restarted on the free plan. Ended with the backend running on Google Cloud Run and
   the website pointed at it, pending a final check.

## What took the most time

By session time and prompt volume, the biggest share went to:
1. **Tailoring quality and validation** (about 4 of the 19 active days), including the Word and
   PDF paths.
2. **Deployment and hosting** (12–13 October), the most intense single stretch.
3. **Bug fixing from your own resume** (4–5 October, 12–13 October), with the most tool use in
   the window.

Tool use: about 4,600 shell commands, 980 file edits and 510 file writes in the window.

## Axis

**Application Architecture.** Most of the work was code, tests and deployment: the tailoring
pipeline, the review and validation rules, the parsers, and the hosting setup. The job-search
features the plan named got less time.

## Against your plan

**Goal was:** Users can search jobs by industry and role with flexible filtering, and get
real-time updates from different job websites. Done looks like steps 3–9 working end-to-end (set
job-search goals, select sources, scout open jobs, clean and validate results, job discovery
dashboard, calculate candidate fit, user triage).

**Honest answer: partly.** Job search, filtering and candidate fit exist and were tested earlier
in the project. But this sprint's time went mostly to resume tailoring quality and getting the
product online, which the plan did not name as the goal. The plan also did not include a
deployment step. I can't confirm from this scan alone that steps 3–9 all work end-to-end on the
live site, because none of the sessions in the window test the live search flow end to end.
