# Decision 028: A Next.js frontend on one FastAPI backend; the Streamlit UI is kept

**Date:** 2026-10-05
**Status:** Proposed (spec 009 awaiting review)

## Context

The builder wants a redesign because the UI looks generic. Streamlit styling is CSS over
internal test ids, and its rerun model limits interaction. Since spec 007 the Streamlit app
runs all logic in-process, while the older `apps/api` backend lacks Apply, Tracker, answers,
email status and SmartRecruiters.

## Options considered

1. **Restyle within Streamlit.** About 1–2 days and keeps everything, but the generic feel
   comes partly from Streamlit's own components and reruns, which CSS can't change.
2. **Next.js plus a thin API over today's in-process modules.** Faster to parity, but needs a
   host with a disk and leaves `apps/api` to drift or be deleted: two backends.
3. **Next.js on `apps/api` grown into the only backend.** Weeks, not days. One backend, and it
   also delivers sign-in and permanent storage.
4. **Design only, build later.** No working change.

## Decision

Option 3, chosen by the builder on 2026-10-05, with a "calm and trustworthy" visual direction.
The deciding reason: one backend that every frontend uses, which also solves sign-in and
storage, instead of a second set of glue to maintain.

The current UI is kept, not retired: it is tagged `ui-streamlit-v1`, it stays in the repo, and
it stays deployable, at the builder's request.

**Rejected: deleting Streamlit at parity.** The builder wants to be able to go back, and both UIs
share the same Python modules, so keeping it costs little.

## What would change our mind

- User tests on the current app show the problems are flow and content, not visual identity.
  In that case, restyle within Streamlit (option 1) and spend the weeks on those problems.
- Phase 1 takes more than about twice its estimate. In that case, stop and reconsider option 2.
