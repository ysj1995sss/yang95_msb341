# Decision 001: Consolidate on job-copilot's architecture + yang95_msb341's engine, instead of maintaining two products

**Date:** 2026-09-21
**Status:** Active

## Context

Two separate implementations of essentially the same product existed at once:

- `yang95_msb341/product/resume_tailorer`: a Streamlit app with a genuinely complete resume-tailoring
  engine (parsing, gap analysis A-E, LLM tailoring with fabrication guardrails, an 85%-alignment
  optimizer loop, PDF generation + a validation hard gate) plus job-search scrapers and ATS
  auto-apply modules -- built single-user, no auth, direct SQLite files.
- `job-copilot`: a separate repo with a real multi-user FastAPI backend (JWT auth, device-token
  pairing for a browser extension), a React dashboard, and a Chrome extension for capturing jobs
  off LinkedIn/Handshake -- but a much thinner resume/profile layer (a naive parser, keyword-overlap
  fit scoring, no PDF export).

Maintaining both meant duplicating effort indefinitely, and neither one alone was both usable
(multi-user, real UI) and capable (the actual tailoring pipeline).

## Options considered

1. **Keep both, pick one later**: no immediate cost, but every future feature has to be built (or
   decided against) twice. Already causing drift -- job-copilot's profile schema and fit scoring
   were noticeably weaker than yang95_msb341's, for no reason other than nobody had ported the
   better version over.
2. **Migrate yang95_msb341's engine into job-copilot**: job-copilot already has the multi-user
   architecture; port the tailoring engine into it. Fastest short-term win, but leaves
   yang95_msb341 (the actual course-graded repo) as the weaker of the two.
3. **Migrate job-copilot's architecture into yang95_msb341, keep yang95_msb341's engine as-is**:
   more work up front, but produces one product in the repo that's actually graded, combining the
   working auth/multi-user layer with the more complete tailoring engine.

## Decision

Went with option 3: built `yang95_msb341/apps/api` as a FastAPI backend modeled on job-copilot's
auth/device/goals/jobs modules, but wired directly to `product/resume_tailorer` via a `sys.path`
shim rather than vendoring a copy -- so the richer resume parser, weighted candidate-fit scorer,
and full tailor-to-PDF pipeline are used natively instead of reimplemented. Deciding reason:
this repo is the one that's graded, so the better product needs to live here, not in a separate
repo nobody else will look at.

## What would change our mind

If job-copilot's web dashboard or Chrome extension turn out to be hard to port (tightly coupled
to job-copilot's own API shape in ways that don't translate cleanly), that would be a signal to
reconsider -- e.g., building a new, simpler UI directly against yang95_msb341/apps/api instead of
forcing job-copilot's frontend to fit.
