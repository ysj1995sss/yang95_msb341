# Decision 010: Steps 4–9 first slice — shared foundation, cf-v2 fit, triage handoff

**Date:** 2026-09-24
**Status:** Active

## Context

Steps 4–9 existed as two parallel stacks (Streamlit SQLite job search vs
`apps/api` Job/UserJob). Candidate Fit was a single weighted score without
explainable eligibility/core/preferred breakdown. APPLY only recorded a triage
label and did not hand the job into Step 10. Deduplication keys disagreed
across stacks, and mock LinkedIn/Indeed/Handshake sources looked as available
as live Greenhouse.

## Decision

Ship a first slice (shared engine in `product/` + API/Streamlit consumers):

1. Shared fingerprint + normalize in `product/resume_tailorer/job_search/`;
   API `dedupe.py` / `normalize.py` delegate to those helpers.
2. Upgrade `CandidateFitScorer` to cf-v2 (`score_fit_detailed` → FitResult)
   with competency-map transferable evidence. Do not create a second scorer.
3. Canonical triage SAVE / APPLY / PASS (legacy interested/skipped/applied
   accepted as aliases).
4. APPLY → Step 10 via `pending_tailor_job` session snapshot consumed by
   `app.py` (JD prefilled + fit banner).
5. Honest source labels: Greenhouse AVAILABLE; LinkedIn/Indeed/Handshake LIMITED.
   Greenhouse mapping populates `raw_json`. Missing sponsorship is NOT_STATED.

## Explicitly out of this round

- New live ATS providers (Lever/Ashby/Workday)
- Separate RawJob / CanonicalJob tables
- Full dashboard filter/sort matrix
- Search-run observability tables

## What would change our mind

If live testing shows cf-v2 overall scores systematically misleading despite
correct evidence classification, recalibrate component weights — do not loosen
truth standards or invent a parallel scorer.
