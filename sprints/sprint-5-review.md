# Sprint 5 Review

**Window:** 2026-11-11 20:56 (plan commit) to 2026-11-23
**Sessions reviewed:** 26 across 1 project (7 sessions in a second project were not read, at your request)

## When you worked

Claude Code prompts fall on 6 of the 13 days so far.

- **Nov 11 (day 1):** the Sprint 5 plan is committed at 20:56, with a short follow-up the same evening.
- **Nov 12 to Nov 15:** no prompts in the project that was read.
- **Nov 16 to Nov 17 (days 6 and 7):** one long push from the afternoon of Nov 16 to the evening of Nov 17. Most of the sprint's prompts fall here, and so do three of the four code commits: the redesign (`7188f8f`, Nov 16 21:25), the phone app pass (`c5331ba`, Nov 17 06:26) and the 16 new games (`7005b39`, Nov 17 11:08). The first tester's written feedback arrives at the end of Nov 17.
- **Nov 19 and Nov 22:** one or two prompts each. A question about resume scores (outside Closer), and a second tester's feedback.
- **Nov 23:** two more testers' feedback, the changes made from all four, and the last commit (`c4488ef`, 23:12).

The shape is a quiet first five days, one long push in the middle, and a smaller round of feedback-driven changes at the end.

## Where you got stuck

- **Context running out in the long session.** The Nov 16 to 17 session ran out of context and had to be continued from a summary four times, and two responses were cut off mid-stream and had to be resumed. Each continuation carried the work forward from the summary.
- **Checking the app in a browser.** The in-app browser pane was hidden, so screenshots timed out. Old service workers from earlier previews served stale pages, which showed up as blank screens. Playwright's offline mode broke page loads even when offline support was working, and network drops on the machine produced false test failures. This ended by moving verification to Playwright scripts with an iPhone-size viewport and accessibility scans, and by testing offline with a real server shutdown.
- **Scroll memory on Nov 23.** Browser checks for "going back returns to where you were" failed several times. The causes were a wrong tour key in the test script (the welcome tour kept opening), the page's smooth scrolling animating instead of jumping, and the click itself scrolling the page. Two code fixes came out of it (instant scrolling, and re-stamping the history entry after render), and the checks then passed 16 of 16 twice in a row.

## What took the most time

By prompt volume, the Nov 16 to 17 push, and within it building the 16 new games: the brainstorm, building them, merging groups, tripling the card pools, then a dogfood pass and three fixes, including splitting the bundle so each game loads on demand. The redesign and the phone app pass (tab bar, Library page, install card, update notice) came before that in the same push. The Nov 23 round of tester-driven changes (Games filter, Help page, back-keeps-your-place, fresh shuffle, narrow-phone depth menu) was the second-largest block.

## Axis

**Design.** Most of the work was interface and usability: the redesign, the phone layout and tab bar, the game screens, and the Nov 23 changes to navigation, filtering and narrow-screen layout made from tester feedback.

## Against your plan

**Goal was:** Get input from 4 people on using Closer installed on their phones, and make the installed experience work better on phones based on what they say.

Input from 4 people came in. Their feedback was forwarded on Nov 17, Nov 22 and Nov 23, and changes were made from it and deployed on Nov 23. Some of it was not acted on yet: the welcome tour, a gentler default depth for teams and families, export and import, and the name.

The sessions do not show that the 4 testers installed Closer to their home screens, which is the first part of "done looks like." The first tester's notes are about the website's pages, say they had not tried the games, and ask how an app runs outside the app store. The other feedback does not mention installing.

The phone app work (tab bar, install card, update notice) was committed on Nov 17, before any tester feedback arrived, so it was not driven by what testers said. The largest block of time went to 16 new games, which the plan did not mention.
