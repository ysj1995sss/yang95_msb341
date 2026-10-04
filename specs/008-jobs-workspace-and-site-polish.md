# Specification 008: Jobs workspace and site polish

**Status:** Approved 2026-10-04.
**Date:** 2026-10-04
**Corrects:** the implementation of spec 007 (decision 025). Spec 007's destinations, safety rules
and visual tokens stay; its Jobs progress strip, numbered Home journey and long-form Career
Profile are replaced.

## Problem

The redesign on `main` follows spec 007's words but not its intent:

- **Jobs** shows a four-step strip (Set goals → Search → Review a role → Prepare application)
  that isn't a real sequence. It reads widget state that Streamlit drops when you leave the page,
  so it says "Set goals — current" while later steps are done. Before any search the page renders
  three mostly empty columns.
- **Tailor** can show "Choose a job first" beside a chosen job, with a blank description, because
  the active job lives only in session state and is lost on a new session or redeploy.
- **Home** draws a numbered journey that completes out of order ("step 4 ✓, step 2 current").
- **Career Profile** is one permanently open form with a provenance badge on every field.
- **Apply and Tracker** empty states are one small box on a large empty canvas.
- **The local-demo warning** is the largest element on every page.

## Baseline (observed 2026-10-04, `main` at e1da2ae)

Product suite **886 passed**; API suite **70 passed**.

## Outcome

Jobs answers one question: *which real role should I prepare an application for?* The rest of
the site stops contradicting itself and looks intentionally composed.

## Jobs

### Presentation-state model

A pure module, `ui/jobs_state.py`, with no Streamlit import, decides what the page shows.

| State | When | Primary action |
|---|---|---|
| `NO_GOALS` | no saved goals and no search this session | Find matching jobs (setup form) |
| `READY_TO_SEARCH` | saved goals, no search this session | Find matching jobs (summary + Edit search) |
| `SEARCHING` | a search was requested this run | none (status line; prior results stay) |
| `RESULTS` | latest search returned rows, none selected yet | first row is selected automatically |
| `DETAIL_SELECTED` | results shown and a row selected | Prepare this application |
| `NO_RESULTS` | the search finished with zero rows | Edit search |
| `PARTIAL_FAILURE` | some sources failed but rows exist | shown as a flag on `RESULTS`/`DETAIL_SELECTED`, never instead of them |
| `SAVED` | the Saved view is active | Prepare this application on the selected saved job |

Inputs are plain values only:
- persisted goals (Career Profile record);
- the latest `SearchRunSummary` (status and per-provider results);
- the current result count;
- the selected job id;
- the active view (Best matches, Newest, Saved);
- a "search requested" flag.

"Goals exist" is never inferred from `st.session_state["job_title"]`.

`PARTIAL_FAILURE` is a flag, not a mutually exclusive state. The model returns
`(state, partial_failure: bool, source_note: str)`.

### Layout per state

- **`NO_GOALS`:** a focused search card in the main area. It leads with target role, location
  and work mode. Role suggestions come from the user's own past titles (no model call) and stay
  editable. "More filters" holds level, industry, minimum salary, sponsorship, job type and
  sources. Primary action: **Find matching jobs**. No results or detail columns are rendered.
- **`READY_TO_SEARCH`:** a one-line summary, e.g. "Product marketing roles · Denver or remote ·
  Mid-level · $90k+", with **Find matching jobs** and **Edit search**. The form stays closed.
- **`SEARCHING`:** the script renders the page with the prior results first and runs the search
  last, updating a status line at the top ("Searching 63 company boards…"). The page never turns
  into a blank spinner.
- **Results (`RESULTS`, `DETAIL_SELECTED`, `SAVED`, `NO_RESULTS`):** a two-region workspace with
  no filter column.
  - **Header bar:** search summary · Edit search · Search again; then "24 matching roles ·
    searched 2:41 PM · Greenhouse, Lever, Ashby". A failed source shows as "Ashby didn't respond",
    not as a failed search.
  - **List, about 38%:** a view selector (Best matches · Newest · Saved), then one `st.radio`
    styled as selectable rows. The label is the role; the caption is company · location · work
    mode (if known) · salary (if stated) · Fit or "Not assessed" · freshness · Saved/Passed. The
    selected row gets a strong left border and tinted background. The list scrolls inside its
    region.
  - **Detail, about 62%,** ordered by decision value:
    1. Role, then "Company · Location · Work mode · posted 3 days ago", then the Candidate Fit
       chip and job quality.
    2. **Prepare this application** (primary), Save, Pass.
    3. **Check before proceeding:** hard requirements and conflicts, kept separate.
    4. **Why this role may fit you:** strong matches (✓) and partial matches (!), each with its
       evidence line.
    5. **Missing from your background** (×).
    6. **Important unknowns** (–): salary, sponsorship and fit when not stated.
    7. **Key requirements and keywords:** missing and present screening terms (the existing
       `ats_keywords` check).
    8. **Read full posting:** a collapsed expander.
    9. Original employer link.
  - **Edit search** opens the same compact form above the workspace. Results stay rendered
    underneath until a new search finishes.
- **Persistence within a session:** results, view, sort and selection survive selecting, saving,
  passing, opening or closing the editor, and visiting another page and coming back. They live
  under non-widget session keys, not widget keys.

### Prepare this application

The button:
- records the APPLY triage;
- sets `pending_tailor_job` from `build_tailor_snapshot` (exact description and fit snapshot);
- stores `active_job_id` in the Career Profile record, so the choice survives a new session;
- clears the previous job's tailoring state and artifact handoff (existing `sync_pending_job`
  rule);
- switches to Tailor.

### Removed

The Jobs `render_progress`/`progress_steps` call and its four labels. No other stepper replaces
them. Progress strips remain only where work is truly sequential (Tailor change review).

## Tailor

- **Job context on load.** If `pending_tailor_job` is missing but the record has an
  `active_job_id` whose posting is in the user's job database, Tailor rebuilds the snapshot from
  it, recomputing fit with the existing scorer. "Choose a job first" appears only when there is
  truly no job.
- **With a job:** a compact header (company, role, Candidate Fit), the resume source, and one
  primary action, **Create tailored resume**. The description is loaded and not shown as an empty
  box. Manual entry moves to a secondary expander, "Tailor for a job that's not in your results".
- **Settings** (length, light touch, model) move into one small expander under the primary
  action. No empty right-hand panels.
- **After tailoring** the review room is unchanged from spec 007, apart from copy: "X of Y
  meaningful changes reviewed". Missing, never added stays visible.

## Home

- The numbered journey becomes a readiness checklist: Resume imported, Facts confirmed, Job goals,
  A role chosen, An application tracked. Each item is Ready, Needs attention or Not started.
  Completion may happen in any order, and there is no "Step N of 5".
- Home still picks one recommended next action, by priority, from what is not ready.
- Returning users see the command center (unchanged logic) with no setup language.

## Career Profile

- **Default view:** "Needs your attention" (count and items) above a summary list, one row per
  section: Contact, Professional summary, Work history (N roles), Education (N schools), Skills
  and tools (N), Certifications, Links, Job goals, Work authorization, Saved answers (N). Each row
  shows a status (Ready, Incomplete, N to review) and an action (Edit, Review, Add, Manage).
- **Editing.** Choosing an action opens that section's editor in a right-hand region on desktop
  (below on mobile), with its own Save. Only one section is open at a time. A section with an
  attention item opens on first visit.
- **Provenance** is shown once per group in the editor header, e.g. "From resume · 2 fields
  edited by you", plus a small marker on edited fields. No per-field badges.
- **New exceptions highlighted:** duplicate skills, a skill listed in both skills and tools, an
  empty field of study, and a role title longer than 80 characters (a likely parse error).
- **Unchanged:** work-authorization answers stay user-entered only. Resume versions move to a
  secondary "Resume source" row.

## Apply and Tracker

- **Apply, empty:** a three-item readiness list ("Choose a real job", "Review the tailored
  resume", "Open the employer's application"). Each item is marked done or not done from real
  state, and one primary action is chosen from the first missing item: Find a job, Finish
  tailoring, or Review readiness. When populated, Apply is unchanged except for density.
- **Tracker, empty:** what is tracked (job, resume version, answers, status history), the status
  lifecycle as a single line, how next actions and due dates appear on Home, and one primary
  action, Find a job. No sample records.
- **Tracker, populated:** saved views ordered Needs action, Ready to apply, Interviewing, Waiting,
  Closed (plus All and Applied). Table and detail unchanged.

## Sidebar

- Navigation, a compact profile readiness line, and the active job.
- A small status block, "Local demo · Shared, temporary data", whose full explanation is in a
  hover/help tooltip and an expander. It replaces the large yellow `st.warning`. Signed-in users
  see their name and Sign out instead.
- The repeated footer line is removed (it is covered by the status block).
- Because an automated test checks for the phrase "Don't share this link", that phrase stays in
  the status block's help text.

## Visual composition

- **Kept:** the palette, Atkinson Hyperlegible, the semantic colours.
- **Changed:**
  - work areas use split layouts (list/detail, summary/editor, review/document) instead of a
    lone card on empty canvas;
  - page headers are tighter (smaller title on work pages, one line of description);
  - one row style is shared by the Jobs list, the Career Profile summary and the Home lists;
  - selected states are visible (border plus tint plus weight);
  - section dividers replace extra bordered boxes.
- **Emphasis** goes to the evidence chain: requirement → verified fact → resume change.
- **Not added:** gradients, blobs, glass, hero sections, card shadows, entrance animations,
  emojis as navigation, sample statistics.

## Responsive

- **1440 and 1024:** two-region layouts as above.
- **390:** search summary and Edit search first, then results, then the selected job below; full-
  width primary actions; evidence groups stacked; no horizontal scroll; Tracker table replaced by
  record summaries under 780px.

## Out of scope

Backend, scorer, tailoring engine, parser, storage format (apart from one new optional
`active_job_id` field), new dependencies, React, auto-submit, browser extension.

## Test requirements

Automated tests, with no browser:

- Goals load from the persisted record, and the state is `READY_TO_SEARCH` with no widget state.
- A finished search never yields a "goals incomplete" state.
- Prior results stay available while the editor is open.
- Changing the view or sort keeps the selection when the job is still listed.
- Saved view works with no search this session.
- The selected job persists across reruns, and selecting another job changes the detail.
- Prepare this application carries the right job id, description and fit snapshot, and stores
  `active_job_id`.
- Switching jobs clears the previous tailoring state.
- Partial provider failure still shows the successful results.
- No-results state.
- Unknown fit, salary and sponsorship are named, never shown as zero.
- Home readiness with out-of-order completion.
- Tailor restores the job from `active_job_id` in a new session, with a non-empty description.
- Empty and populated states for Apply and Tracker.

Browser tests (synthetic data only):
- Jobs: no goals, saved goals, searching, results, selected, saved, no results, partial failure.
- Every destination at 1440×900, 1024×768 and 390×844, with before/after captures reviewed in the
  pane.

## Acceptance criteria

The completion standard in the request applies as written, including a closing critique against
`Sample\My product`.
