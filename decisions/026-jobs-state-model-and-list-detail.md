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
