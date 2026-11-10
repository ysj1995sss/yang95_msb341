# Sprint 4 Review

**Window:** 2026-10-26 22:45 (plan commit) to 2026-11-09
**Sessions reviewed:** 20 across 1 project (7 sessions in a second project were not read)

## When you worked

Claude Code prompts fall on 2 of the 14 days, plus the plan commit on day 1.

- **Oct 26 (day 1):** the Sprint 4 plan is committed at 22:45.
- **Oct 27 (day 2):** a short session, about 2 prompts, that builds the Sprint 4 features. The session history carries a summary of that work into later sessions.
- **Oct 28 to Nov 8:** no prompts in the project that was read.
- **Nov 9 (day 14):** about 31 prompts between roughly 11:45 and 18:45. All the commits for this sprint's work are on this day.

The shape is front-loaded, then a gap of 12 days, then one long push on the last day. The first commit of the Sprint 4 features (`a9ae927`) is 2026-11-09 11:46. Git has nothing for the Sprint 4 code before that.

The 7 unread sessions could contain activity on other days, so the gap is for the read project only.

## Where you got stuck

1. **Getting the new version live on the public address.** Prompts on Nov 9 return several times to updating the live site: how to update it by hand, a screenshot of a promote dialog that refused, then "upload in Vercel". The cause was that pushes to the working branch only produced preview builds, while production was tied to the `main` branch. It ended when the Closer work was merged into `main` and a production build of it finished.
2. **Separating the Closer work from the Job Copilot work in git.** Three prompts ask for the Closer work to be kept apart from the other work, ending with a request to merge it. It ended with a Closer-only commit fast-forwarded onto `main` at 18:07, with no other files changed.
3. **Deciding what to change after tester feedback.** The prompts paste feedback from two testers and ask for questions about what to change. It ended with three decisions: remove the text box, add a plain description line to the home page, and make the site installable.

## What took the most time

By prompt volume on Nov 9, about 11 of 31 prompts are about getting the work live and onto `main` (Vercel access, checking builds, promoting, branch separation, the merge). The next largest group is about 6 prompts of building and fixing: committing Sprint 4, a QA pass, a debugging pass, and the 17-feature request. The remaining prompts are checking the result, asking what to do next, and sprint close-out.

Session duration was not available from the scan, so this is by prompt volume and commit times. The commit times run from 11:46 (Sprint 4 features) to 18:07 (Closer-only change on `main`).

## Axis

**Application Architecture.** Most of the work was code, tests, deployment and repository structure: the installable app and its offline service worker, the data and session logic, the Vercel production setup, and the branch separation.

## Against your plan

**Goal was:** Expand Closer's question library to 500 unique questions across all 10 categories, with 50 questions for each category. Add progressive question depth, Guess My Answer, favorites, trivia scoring, and randomized questions without repetition.

The work matches the goal. At the end of the window `main` holds 500 questions (50 per category), four depth levels, favorites, trivia scoring, randomized questions with no repeats, and Guess My Answer, all live on the public site. Two testers reported what they found, and the work was changed in response to it.

The window also holds work the plan did not ask for: a 17-feature set (install button, dark mode, table mode, debate mode, seasonal packs, audience filter and others), and the repository and deployment changes above.
