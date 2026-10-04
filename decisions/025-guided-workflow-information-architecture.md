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

## Implementation record (2026-10-04)

Built on branch `redesign/guided-workflow` in three commits (Phase 0; Phases 1–7; Phases 8–9
fixes), then docs.

**Built as specified:** the six-destination rail with identity, profile readiness and the active
job; per-page progress strips instead of the global ribbon; Home first-time journey and returning
command center; Career Profile with provenance and review by exception; Jobs master-detail with
hard gates and unknowns; Tailor review room with exact PDF preview (rendered page images, sticky
on desktop through a CSS `:has()` rule); Apply readiness and Mark as applied; Tracker table,
six saved views, detail panel and weekly goal.

**Where the build differs from the spec, and why:**

- **Tailor lives at `pages/5_Tailor.py`** (spec said `pages/tailor.py`); numbered like the other
  pages so the file order stays readable.
- **Apply's preview is implicit.** "Track this application" runs the dry-run preview and then
  stages in the same click, against exactly what the checklist shows. Decision 021's rule is
  kept (the staged record matches what was previewed; a preview alone never saves anything),
  but the user no longer has to click Preview first. Manual mode only records; it never submits.
- **No demographic fields.** Nothing in the product uses them, so storing them would only add
  risk. EEO questions on a form are answered by the user through the approved answer bank.
- **The Streamlit app no longer uses the FastAPI profile.** `profile_review/api_client.py` and the
  API are unchanged for their own clients; linking them is future work.
- **Screenshots were reviewed in the browser but not committed**, to keep binary files and any
  chance of personal data out of the repo.

**Verification:** product 874 passed, API 70 passed. The full journey (Home → Career Profile →
goals → Jobs → Tailor → Apply → Tracker → Home) is an automated test
(`tests/test_workspace_flow_e2e.py`) and was walked in the browser at 1440px and 390px with a
synthetic resume, live Greenhouse/Lever/Ashby results and the configured model. States seen:
empty (first visit, no search, no applications), populated, warning (artifact passed with
warnings), blocked (a failed artifact is refused by Apply, tested), loading (search spinner,
tailoring status) and failure (search with no reachable source).

**Found during verification and fixed:** primary-button text contrast (2.6:1); a misleading
"your resume already covers this posting" message when every proposal had been rejected by the
checks; a skill cited as support for an edit that didn't add it; a literal "None" shown as
evidence; a job chosen in an earlier session not carried into Tailor; an unrecognized degree not
flagged; two dev-server reload hazards (decision 021) that silently skipped all sources or sent
Manual mode down the ATS-parsing path.

**Found and not fixed here (follow-ups):**

- The fit scorer counts the skill "Go" as matched by "go-to-market" (flagged as a separate task).
- The resume parser finds no jobs in the common one-line "Title | Company | Dates" layout, and
  the DOCX splice pipeline only sees real Word list bullets (`numPr`), not typed "•" bullets.
- The gap analyzer sometimes returns whole job-description sentences as requirements; the UI
  now shortens them, but the analyzer should split them.
