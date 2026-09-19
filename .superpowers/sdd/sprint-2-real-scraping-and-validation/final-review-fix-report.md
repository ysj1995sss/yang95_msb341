# Final Review Fix Report — Sprint 2 (Real Scraping + URL Validation)

All 5 issues from the whole-branch review (1 Critical, 2 Important, 2 Minor) fixed in one pass.

## Fix 1 (Critical) — Filter real Greenhouse postings by `goals` before validation/storage

**File:** `product/resume_tailorer/job_search/scrapers/greenhouse_scraper.py`

- `_scrape_real()` (line ~87) now returns `self._filter_by_goals(all_jobs, goals)` instead of the raw `all_jobs`.
- New `_filter_by_goals()` (line ~106): case-insensitive substring match of any goal-title keyword (>2 chars) against `job.title`. Empty/keyword-less goal title is a pass-through (returns all jobs).
- Location is deliberately **not** filtered here — free-text Greenhouse locations are already handled downstream by `database.search_jobs()`'s LIKE filter; duplicating it risks over-filtering.

**Impact:** for a typical specific-title search the working set drops from the measured ~1,372 postings to roughly a handful–few dozen. At ~0.84s/HEAD plus the new 1 req/sec floor, that is ~1 req/sec × N, i.e. roughly 10–40 seconds instead of ~19 minutes of blocking work inside the Streamlit spinner.

**Tests:** `test_scrape_real_filters_postings_by_goal_job_title` (a "Marketing Manager" posting is dropped when the goal is "Software Engineer"), `test_filter_by_goals_returns_all_when_no_job_title`.

## Fix 2 (Important) — Rate limiting in `URLValidator`

**File:** `product/resume_tailorer/job_search/url_validator.py`

- Added `import time`, `MIN_REQUEST_INTERVAL = 1.0`, `__init__` setting `self._last_request_time = 0.0`, and `_respect_rate_limit()` mirroring `BaseScraper._respect_rate_limit()` (elapsed-since-last, sleep the remainder, re-stamp).
- `check_url()` calls `self._respect_rate_limit()` as its first statement, before the `requests.head()` try block.

This brings the measured ~1.19 req/sec against `boards.greenhouse.io` under the 1 req/sec-per-domain constraint.

**Test impact verified:** every test in `test_url_validator.py` constructs a fresh `URLValidator()`, so `_last_request_time` starts at 0.0 and the first `check_url()` is never delayed (elapsed since epoch ≫ 1.0s). The one test that exercises multiple URLs (`test_filter_active_jobs_keeps_active_and_unknown_drops_closed`) patches `check_url` itself, so no sleep occurs. `test_job_service.py` patches `URLValidator.check_url` via an autouse fixture, likewise unaffected. Measured suite durations are unchanged (slowest tests are the pre-existing scraper rate-limit tests).

**New tests:** `test_check_url_respects_rate_limit_between_consecutive_calls` (asserts exactly one `time.sleep` of ≤1.0s across two back-to-back calls, with `time.sleep` mocked) and `test_first_check_url_call_is_not_delayed`.

## Fix 3 (Important) — NULL/"Unknown" `work_mode` passes the `remote_preference` filter

**File:** `product/resume_tailorer/job_search/database.py` (`search_jobs()`, ~line 206)

Before: `where_clauses.append("work_mode LIKE ?")`
After: `where_clauses.append("(work_mode LIKE ? OR work_mode IS NULL OR work_mode = 'Unknown')")` — `params.append(f"%{goals.remote_preference}%")` unchanged, so it remains a drop-in single-placeholder replacement and `cursor.execute(query, params)` is untouched.

This mirrors how salary NULLs are already handled a few lines above, and matches the URLValidator principle that ambiguous cases are kept, not dropped. Without it, any user selecting remote/hybrid/onsite got 0 real results while the UI still showed the "Live Data" banner.

**Test:** `test_search_jobs_unknown_work_mode_passes_remote_preference` in `product/tests/test_job_database.py` — a `work_mode="Unknown"` job is returned for `remote_preference="remote"` while an explicit `work_mode="on-site"` job is still excluded (confirming the filter is relaxed, not disabled).

## Fix 4 (Minor) — Reset `data_source` at the top of `scrape()`

**File:** `product/resume_tailorer/job_search/scrapers/greenhouse_scraper.py` (line ~73)

`self.data_source = None` is now the first statement of `scrape()`, before `real_jobs = self._scrape_real(goals)`. A scraper instance retained by the JobService cache can no longer report a stale `"real"`/`"mock"` value from a previous call if a later call returns `[]` via the except path.

## Fix 5 (Minor) — Title-cased company display name

**File:** `product/resume_tailorer/job_search/scrapers/greenhouse_scraper.py` (`_map_greenhouse_job`, ~line 168)

`company=board_token` → `company=board_token.replace("-", " ").replace("_", " ").title()`. `"airbnb"` → `"Airbnb"`, `"some-co"` → `"Some Co"`. Still literally the board token, just formatted; no extra API call.

**Tests:** added an assertion to `test_scrape_maps_greenhouse_fields_correctly` and a dedicated `test_map_greenhouse_job_title_cases_board_token`. No existing test asserted the raw lowercase value.

## Stale test updated by Fix 1

`test_scrape_handles_missing_optional_fields_as_unknown` fed a "Data Analyst" posting while the goal title was "Software Engineer". With Fix 1 in place the posting was correctly filtered out and the scraper fell back to mock data, breaking the test's intent. The goal title was changed to `"Data Analyst"` so the test still exercises the real-API mapping path it was written for.

## Verification

```
cd product && python -m pytest tests/ -q
182 passed in 67.84s
```

Up from 176 — 6 new tests: 3 in `test_greenhouse_scraper.py`, 2 in `test_url_validator.py`, 1 in `test_job_database.py`. Slowest tests are pre-existing `BaseScraper` rate-limit sleeps in the Greenhouse mock-fallback tests (~5s each), not the new `URLValidator` rate limit.
