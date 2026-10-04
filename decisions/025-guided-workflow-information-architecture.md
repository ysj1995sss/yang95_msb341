# 025: Six-destination guided workflow

**Date:** 2026-10-04
**Status:** Accepted 2026-10-04 (spec 007 approved; profile stored as a per-user file, option A).

## Context

Decision 019 organised the app into five tool-named workspaces (Fact Vault, Job Discovery,
Tailoring Studio, Apply Launchpad, Application Tracker) with a four-step ribbon on every page.
Reviewing the whole flow (2026-10-04) and four competitor products found:

- Only about 10 of the 24 spec steps are real user decisions; the rest are system work the user
  should not see as steps.
- A new user has no starting point. There is no home screen and no single "next action".
- A resume is uploaded twice (Fact Vault and Tailoring Studio) into two stores. Fact Vault needs a
  separate login to a service that must be running locally, so the first step cannot be finished
  on the deployed app.
- Apply asks the user to paste a Job ID and a PDF path that the app already knows.
- The global ribbon is meaningless on pages whose task it does not describe.
- There is no explicit "Mark as applied", although the status mechanism exists.

## Decision

Adopt six user-facing destinations: **Home, Career Profile, Jobs, Tailor, Apply, Tracker**, with a
contextual progress model per page instead of a global ribbon, and a five-milestone setup journey
on Home that turns into a daily command center once complete.

Keep Streamlit, every engine, the per-user storage, and every safety gate. Manual mode is the
default and only reliable application path; Assist and Auto stay visibly disabled until spec 006
is proven. Completeness is shown as defined required and optional sections, not a percentage.

Pending separate approval (spec 007, Open decision 1): store the Career Profile as one versioned
file in the user's existing per-user folder so a resume is entered once and reused.

## Rejected

- **Keep five workspaces and add a Start Here page.** This is what the first draft did. It adds a
  sixth page without giving a returning user a command center, and leaves the ribbon.
- **Copy a competitor's flow** (long mandatory setup, autonomous apply, marketing home). Conflicts
  with decisions 012 and 016 and the non-negotiable truth rule.
- **React or another front end.** No requirement here needs one.
- **A percentage completeness score.** It would imply precision the parser does not have.
- **Kanban first.** The table and detail view must be finished and tested before any board.

## Consequences

- The Tailoring Studio moves out of `app.py` so Home can be the entry point (file move only).
- Decision 019's navigation and ribbon are superseded; its visual system, semantic color rules and
  safety rules remain in force.
- Tokens change slightly (ink `#172033`, canvas `#F3F6FA`, line `#D7DEE8`, verified `#167A5A`,
  review `#A86108` on paper only, blocked `#B43A45`, muted `#5D6878`). Amber on the canvas fails
  AA at 4.4:1 and needs the darker `#9A5806`.
