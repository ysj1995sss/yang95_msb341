# 026: Jobs becomes a stateful job browser; site corrections to spec 007

**Date:** 2026-10-04
**Status:** Accepted 2026-10-04.

## Why the Jobs stepper is removed

The four-step strip (Set goals → Search → Review a role → Prepare application) did not describe
a real sequence:

- Searching without saving goals is valid.
- Reviewing several roles is not a step.
- Preparing an application happens in Tailor and Apply, not in Jobs.

It was computed from widget state that Streamlit deletes when you leave a page, so it showed
contradictions such as "Set goals — current" after a search. It also took the page's most
valuable row. A progress strip suits only sequential work, such as reviewing resume changes, so
Jobs gets none.

**Rejected:** fixing the step calculation. A correct number still describes the wrong mental
model.

## Why search is state-based

Jobs now derives its layout from a pure presentation-state model (`ui/jobs_state.py`). The
inputs are persisted goals, the latest search summary, the result count, the selection, the
active view and whether a search was requested. Each state has one primary action, and nothing
is rendered before it's useful.

A partial source failure is a flag on the results states, not a separate state. One board not
answering must never hide jobs from the boards that did.

**Rejected:** keeping the derived-from-widgets approach with more guards. It caused the current
bug, and it can't be unit-tested.

## Why results use list/detail after search

After a search the decision is between roles, not about filters. A permanent filter column
spent a third of the width on settings the user had already chosen. The workspace becomes a
roughly 38/62 list and detail, and the search form collapses into a one-line summary with Edit
search.

Rows are one styled `st.radio`:
- one widget instead of three buttons per row;
- keyboard accessible;
- no horizontal scroll on phones;
- a visible selected state through CSS.

**Rejected:**
- `st.dataframe` with row selection: it scrolls sideways on mobile, and its cells can't show fit
  tones.
- Per-row button cards: these are the clutter we're removing.

The detail panel puts the fit explanation (hard conflicts, matches, gaps, unknowns, key terms)
before the full posting, which is collapsed. The evidence is the reason to use Job Copilot.

## Active job survives a new session

The record gains one optional field, `active_job_id`. Tailor uses it to reload the chosen job,
with its description and a recomputed fit, when the session has lost it. This removes the
"Choose a job first" plus empty-description contradiction.

**Rejected:** persisting the whole tailoring state; it's large and includes generated files.

## What stays from decision 025

- The six destinations.
- The per-user Career Profile file.
- Provenance and review-by-exception.
- Manual as the only available mode.
- Mark as applied.
- The Tracker table and detail.
- Tokens and typography.
- Every safety gate.

Home's numbered journey becomes a readiness checklist. Its items can complete in any order, so
it can't show an impossible sequence. Career Profile's open form becomes a section summary with
one editor at a time. The yellow local-demo warning becomes a compact status that is still
honest.

## Implementation record (2026-10-04)

Built on `redesign/jobs-workspace` in nine commits, one per phase, plus fixes found in the
browser. Baseline before: product 886, API 70. After: **product 925, API 70**.

**Built as specified:**

- **Jobs:**
  - `ui/jobs_state.py` and its tests.
  - No stepper; one setup card when there are no goals; a saved-search summary.
  - Searching keeps prior results on screen.
  - A 38/62 list and detail with Best matches, Newest and Saved.
  - A styled radio list; partial-failure note; no-results card.
  - Detail ordered by decision value; the full posting collapsed.
- **Tailor:**
  - "Prepare this application" persists `active_job_id`, and every page restores the job in a
    new session.
  - The tailored-resume handoff is persisted too, restored only when the exact file and checksum
    still match.
  - One primary action when a job is loaded; manual description entry is secondary.
- **Home:** a readiness checklist in any order. **Sidebar:** a compact `<details>` demo status.
- **Career Profile:**
  - a section summary with one editor at a time;
  - likely parse problems are flagged and opened first;
  - provenance once per section.
- **Apply and Tracker:**
  - Apply and Tracker empty states each have one next step.
  - Tracker views are ordered by action, and phones get summaries instead of the table.

**Found in browser checks and fixed:**

- **Duplicate titles:** two postings with the same title (one role in two cities) made the
  highlighted row and the selected job disagree. Labels are now kept distinct.
- **`$` signs:** salaries in captions were rendered as LaTeX maths.
- **Edit search:** the editor reopened empty after the form had been hidden.
- **Header during a search:** the header described the new search before its results arrived.
- **"Nothing missing" overclaim:** the detail claimed nothing was missing when fit hadn't been
  assessed.
- **Tablet width:** buttons were truncated, and the Saved view option was hidden.
- **Career Profile on phones:** each row stacked into three.

## Critique against `Sample\My product`

| Screenshot problem | Now |
|---|---|
| Jobs stepper says "Set goals — current" with goals saved | No stepper; a saved search is a one-line summary with Find matching jobs |
| Three mostly empty columns before searching | One setup card (or summary) and a short side note; no empty regions |
| Tailor "Choose a job first" beside a chosen job, empty description | The job is restored from the profile; one Create tailored resume action; no empty box |
| Home step 4 ✓ while step 2 is current | A checklist of Ready / Needs attention / Not started; "3 of 5 ready" |
| Career Profile one long open form, a badge on every field | A section summary; one editor; provenance once per section |
| Apply and Tracker single box on empty canvas | Readiness steps or a tracking explainer with one primary action and a side note |
| The yellow warning dominates every page | A one-line expandable status |

**Still weak, honestly:**

- **Search speed.** The first search still takes about 20–30 seconds behind a status line.
  That's network-bound, not layout.
- **Streamlit markup dependence.** The result list styling relies on Streamlit 1.64's radio
  markup (`data-selected`, `stRadioOption`). A Streamlit upgrade could break it; the behaviour
  would still work, only the styling would degrade.
- **Desktop whitespace.** Pages still have empty space below the content on tall screens when
  there's little to show (Home first-time, empty Apply). It's less dominant, but not eliminated.
- **Evidence quality.** Fit evidence quality is limited by the scorer. The "Go" ↔
  "go-to-market" false match is still open as a separate task.
- **Tailoring state.** Review decisions in Tailor live in the session. A new session restores
  the tailored resume and its review status, but not the per-change decisions.
