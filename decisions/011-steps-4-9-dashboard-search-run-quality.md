# Decision 011: Steps 4–9 dashboard filters, search-run tracking, job quality

**Date:** 2026-09-24
**Status:** Active

## Context

Decision 010 shipped the Steps 4–9 first slice (fingerprint/normalize, cf-v2 fit,
canonical triage, APPLY → Step 10). Explicitly deferred were the full dashboard
filter/sort matrix, search-run observability, and stale/expired/broken quality
states. Without those, the discovery UI only filtered by triage status, a failed
scraper was invisible (`except: pass`), and expired or stale postings looked
identical to fresh ones.

## Decision

1. **Shared dashboard helpers** in `product/resume_tailorer/job_search/dashboard.py`
   (`DashboardFilters`, `filter_and_sort_jobs`, `filter_api_job_dicts`) drive both
   Streamlit and `GET /jobs` so filter/sort stay in parity.
2. **SearchRunSummary** is the return value of `JobService.search_and_store`.
   Each source is isolated (`ok` / `failed` / `skipped`); one failure yields
   `partial` and does not abort other providers. Closed-URL drops are counted
   as `closed_filtered`.
3. **JobQualityStatus** (`active` / `stale` / `expired` / `broken` / `unknown`)
   is computed at read time from deadline, posted age (default 45 days), and
   optional URL status. Confirmed-closed URLs still are not stored; quality
   labels honesty for what remains.
4. **API list parity**: `GET /jobs` accepts `min_fit`, `max_fit`, `min_salary`,
   `sponsorship`, `work_mode`, `source`, `quality`, `keyword`, `sort_by`,
   `sort_dir`, and returns `quality_status` on each item.

## Explicitly out of this round

- Persisted search-run / RawJob tables (in-memory + session summary is enough)
- Live URL revalidation of every stored job on every dashboard load
- New ATS providers beyond Greenhouse

## Alternatives considered

- **Return `int` from `search_and_store` and stash summary on the service only** —
  rejected; callers need the summary for UI feedback, and `total_stored` is the
  explicit count field.
- **Drop stale/expired at ingest** — rejected; users should see and filter them
  rather than silently losing context.
- **Duplicate filter logic in FastAPI vs Streamlit** — rejected; shared helpers
  prevent drift.

## What would change our mind

If search-run history across sessions becomes a product requirement, add a
lightweight `search_runs` table. If stale thresholds need per-user control,
expose `stale_days` in goals rather than a constant.
