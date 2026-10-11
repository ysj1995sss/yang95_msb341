# Agent usability walkthroughs: release workflows

Date: 2026-10-11. Scope: spec 015, authorized release steps 1–13.

These are three **agent simulations**, assembled from the root agent's actual browser
observations and test results during the release run. They are not interviews or
independent human usability research. Human participants: **0**. No task times,
satisfaction ratings, participant quotes or user approvals were collected or invented.
The scenarios below describe what the agent did and what the interface showed.

Data: the synthetic resume fixture and an explicit scratch workspace shared by the
test Streamlit and Next.js apps. Public company/job names identify observed boards,
not participant information. Employer applications submitted: **0**.

## A01 — First-time profile, search and preparation

The agent imported the synthetic resume through Streamlit. Education needed review
after parsing a BS education entry, and the profile contained a duplicate Tableau
tool entry. The agent corrected the education entry and confirmed the remaining facts.
This establishes a usable correction path; it also shows that import still requires
attention before the person can trust every parsed field.

Searching for Data Analyst checked 75 boards and returned 69 roles. Opening the web
app showed the same Career Profile. The agent added Watershed's board through the
web interface; platform verification reported 35 open roles. A subsequent search
checked 76 boards and returned 69 roles under the active search filters. Board
verification counts and filtered search counts measure different things.

The agent saved a Cursor role and opened the existing real-model review across
frontends. That review had zero proposed changes; this scenario reused the saved
review rather than generating another model response. The PDF could be downloaded.
On Apply, the agent tracked the application, then opened Tracker. Tracker showed one
ready-to-apply application and its applied state as **Not yet**. No employer form
was submitted.

Observed strengths: profile and review persistence across frontends, board addition,
PDF access and the preparation-to-Tracker handoff worked in the scratch workspace.
Observed friction: a first-time person must understand the education review warning
and inspect parsed facts rather than assuming the imported profile is already right.

## A02 — Returning user, interrupted batch and profile correction

The agent used a three-role batch: Cursor User Operations, Lyft People, and Lyft GTM.
Tailoring used the real Codex CLI model. After **Stop after the current job**, two
items were done and the third was skipped. Continuing the batch resumed the third
item.

The agent stopped only the experiment's test server during that model run. After
restart, the batch showed stopped state and preserved the two completed items.
Continuing the one remaining item produced three completed items. A fresh Streamlit
Jobs page after restart showed the saved batch without requiring another search;
that behavior was verified after the release-run fix.

The agent then removed the duplicate Tableau tool entry through the web profile
editor. All three reviews were flagged **Profile changed**. The single-job Apply
screen disabled tracking and displayed **Resume missing** in the kit, while batch
Prepare returned **Tailor again** for all three items. These guards stopped preparing
a resume tied to the older profile.

Tailoring the Cursor item again with the real model made that item's review current
while preserving the other batch results. The other two items still needed tailoring
against the edited profile. The test did not establish that all three were ready
again after the single-item redo.

Observed strengths: completed work survived stop, continuation and process restart;
profile-version guards prevented stale preparation; redoing one item retained the
rest of the batch. Observed friction: a small duplicate-tool correction marks every
review stale, including reviews that might not use the changed fact. This is the
existing conservative policy, not proof that selective invalidation is implemented.

## A03 — Keyboard access and interpretation of evidence

The existing browser suite passed **22 Playwright tests**, including keyboard access
on every destination and phone layout/light-and-dark-theme automated accessibility
checks. This is automated evidence. No human NVDA or VoiceOver session was performed,
and these results do not establish a manual screen-reader pass or complete WCAG
conformance.

During the real-model review, the model associated a listed Tableau tool with a SQL
project without explicit evidence that Tableau was used on that project. The root
agent reviewer rejected that rewrite. Keeping a true tool somewhere in a profile
does not support assigning it to any particular project or role.

Requirement evidence also needs more specificity: an observed survey-platform
requirement involving Qualtrics was labelled direct when the available passage
contained SQL/Tableau evidence. Treat this as a residual quality risk in requirement
matching and presentation. The observation is not evidence that the person possesses
Qualtrics or that the resume passes an employer's screening system.

Next work should have a separate spec and focused reproductions for project-specific
tool attribution and platform-specific requirement evidence. The release batch work
did not resolve those quality risks. Continue reviewing model rewrites against the
exact supporting passage before accepting them.

## Limits and real participant follow-up

The subsequent PDF exercise completed: a real-model run proposed a skills reorder,
then an explicitly seeded synthetic Summary/Skills review exercised rejection, acceptance,
manual editing, reload and rebuilding. The seed is not a model response. A missing
section newline initially merged Skills with EDUCATION; the reproduced regression was
fixed and browser version 4 preserved separate sections in a one-page PDF. Streamlit
also loaded both saved decisions and reported Ready for Apply. See the release ledger
for the confirmed-profile precedence qualification and full evidence. Hosting/account
integrations and independent human feedback remain separate from these scenarios.

Run the anonymous `P01`–`P03` participant study and manual screen-reader protocol in the
[release checklist](../../docs/release-readiness-checklist.md) before drawing conclusions about how job seekers
understand the product. Preserve observed task outcomes and actual consented feedback;
do not relabel A01–A03 as people or use agent completion as human approval.
