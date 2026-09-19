# Task 3 Report: Wire URL Validation into JobService and Show Data Source in UI

**Status:** DONE

**Commits:** 18e3d99

**Test Summary:** 176 passed (175 prior + 1 new: `test_search_and_store_filters_out_closed_job_urls`). Full suite `pytest tests/ -q` in `product/` ran clean in ~63s.

## What was done

### `product/resume_tailorer/job_search/job_service.py`
- Added `from resume_tailorer.job_search.url_validator import URLValidator`.
- Added `self.url_validator = URLValidator()` in `__init__`, alongside the existing `self.deduplicator` / `self.fit_scorer` instantiations.
- In `search_and_store`, inserted a filtering step between the existing `deduplicated_postings = self.deduplicator.deduplicate(all_postings)` line and the store loop:
  ```python
  deduplicated_postings = self.url_validator.filter_active_jobs(deduplicated_postings)
  ```
  The actual local variable name in this file is `deduplicated_postings` (not the brief's illustrative `deduplicated`), and the store loop variable is `stored_count` (matches the brief). Updated the method's docstring orchestration list to mention the new step 3b.

### `product/resume_tailorer/pages/2_Job_Search.py`
- The search button's click handler lives in `_render_search_button(form_data, sources)`; its local variable for selected sources is `sources` (not `selected_sources` as in the brief's illustrative snippet), and it already holds a `service` reference from `_get_job_service()`.
- After `service.search_and_store(goals, sources)` succeeds, added a check using `service._get_scraper(JobSource.GREENHOUSE)` (guarded by `JobSource.GREENHOUSE in sources`) and `getattr(greenhouse_scraper, "data_source", None) == "real"` to decide between a `st.success` "Live Data" banner and a `st.warning` "Demo Mode" banner, per-search-result rather than as a static top-of-page banner.
- Removed the old static "Demo Mode" `st.warning` block that lived in `main()` right after `st.caption(...)` and before `_render_search_goals_form()` — its exact prior text was:
  > "⚠️ Demo Mode: Job listings shown are simulated placeholder data for testing the search/filter/triage flow. Real scraper integrations (LinkedIn, Indeed, Handshake, Greenhouse APIs) are a follow-up item — see decisions/ for tracking. Real job data will never be fabricated once live scraping is integrated; only actually-scraped fields will be shown, with 'Unknown'/'Not specified' for anything a real posting doesn't provide."

  It is now shown conditionally (still using the emoji glyphs, escaped as `⚠️` / `✅` in source to survive Windows console encoding) only after a search runs, reflecting whether Greenhouse actually returned real data for that specific search.
- Verified with `python -c "import ast; ast.parse(open('resume_tailorer/pages/2_Job_Search.py', encoding='utf-8').read())"` — required explicit `encoding='utf-8'` because the file contains non-ASCII characters (em dash, emoji) and the default `open()` codec on this Windows machine is `gbk`, which fails to decode them. This is a pre-existing environment quirk unrelated to the edit; the file itself is valid UTF-8 and parses fine.

### `product/tests/test_job_service.py`
- `JobService`, `SearchGoals`, `JobPosting`, `JobSource` were already imported at module level, so the new test does not re-import them (deviating from the brief's illustrative snippet, which re-imports them locally).
- Deviated from the brief's test body in one respect: the brief's illustrative test builds its own `goals` object matching the job characteristics (title "Engineer", location "Remote") rather than reusing the file's existing `sample_goals` fixture (title "Software Engineer", location "San Francisco, CA"). Initially I reused `sample_goals` to match file conventions, but that made the test fail after implementation — not because filtering was broken, but because `get_available_jobs`/`db.search_jobs` filters stored jobs by matching the given `SearchGoals` (title/location), and the mock jobs' `location="Remote"` didn't match `sample_goals.location="San Francisco, CA"`, so neither job showed up in the query results even though the active one was correctly stored. Switched to building the goals object exactly as prescribed in the brief for this test, keeping other tests on `sample_goals` as before.
- Test uses `mock.MagicMock()` / `mock.patch` (module already imports `from unittest import mock`), consistent with the rest of the file's style, rather than the brief's `from unittest.mock import patch, MagicMock`.

## Concerns

None outstanding. One note for awareness: `URLValidator.check_url` makes a real `requests.head` call for any job with a URL, so `search_and_store` now does live network I/O per job unless `_get_scraper` is mocked and URLs point to real/fake domains. In this sandboxed test environment those calls fail fast (connection error) and are treated as "unknown" (kept, not dropped), so existing tests using `https://linkedin.com/job/...` style URLs still pass — full suite ran in ~63s with no timeouts. If a future environment has slower failure fallback (e.g. DNS resolution succeeding but connect timing out), `search_and_store` could become slow when scraping many postings; this is inherent to `URLValidator`'s design (Task 2, already completed/accepted) and out of scope for this task to change.

## Fix Round 1

**Status:** DONE

**Commits:** (see below, filled in after commit)

**Test Summary:** 176 passed (`pytest tests/ -q` in `product/`), 61.95s wall time (down from the ~160s observed after the original Task 3 landed, back in line with the pre-Task-3 ~60-70s baseline). `pytest tests/test_job_service.py -v` shows all 14 tests in the file passing in 0.40s — confirming no live HTTP calls remain in that file's test run.

### Finding 1 fix (scraper caching so the UI's data_source read is meaningful)

`product/resume_tailorer/job_search/job_service.py`:
- Added `self._scraper_cache = {}` (a plain dict keyed by `JobSource`) to `JobService.__init__`, right after `self.scraper_map` is built.
- Changed `_get_scraper` from unconditionally calling `scraper_class()` on every call, to: check `self._scraper_cache` first and return the cached instance if present; otherwise instantiate via `self.scraper_map.get(source)`, store it in the cache, then return it.
- Net effect: within a given `JobService` instance's lifetime, calling `_get_scraper(JobSource.GREENHOUSE)` always returns the SAME `GreenhouseScraper` instance. `search_and_store()` calls `_get_scraper` internally to run `.scrape()` (which sets `.data_source` to `"real"` or `"mock"`); a later call to `_get_scraper(JobSource.GREENHOUSE)` from the Streamlit page (`product/resume_tailorer/pages/2_Job_Search.py`, in `_render_search_button`) now gets back that exact same, already-scraped instance, so `getattr(greenhouse_scraper, "data_source", None) == "real"` correctly reflects what just happened. No changes were needed in `2_Job_Search.py` itself — its existing call pattern (`service._get_scraper(JobSource.GREENHOUSE)` after `search_and_store` returns) was already correct in intent; it was only broken because the underlying method handed back a fresh, unscraped instance every time.
- Verified manually (not just via existing tests, since none of them exercised the caching behavior directly): instantiated a `JobService`, called `_get_scraper(JobSource.GREENHOUSE)` twice, confirmed `is` identity, then set `.data_source` on the first reference and confirmed the second reference reflected the change.

### Finding 3 fix (scope URL validation to real Greenhouse postings only)

Read `base_scraper.py` and `greenhouse_scraper.py`: `data_source` is set only on `GreenhouseScraper` (in `__init__` as `None`, then to `"real"`/`"mock"` in `scrape()`); `BaseScraper` has no `data_source` attribute at all, so `LinkedInScraper`, `IndeedScraper`, and `HandshakeScraper` instances have no such attribute (mock-only, no real/mock distinction).

`product/resume_tailorer/job_search/job_service.py`, `search_and_store`:
- While looping over `sources` to scrape, additionally captured `greenhouse_data_source = getattr(scraper, "data_source", None)` whenever `source == JobSource.GREENHOUSE`.
- After deduplication, only call `self.url_validator.filter_active_jobs(...)` when `greenhouse_data_source == "real"`, and even then, scope it to just the subset of `deduplicated_postings` whose `.source == JobSource.GREENHOUSE` — split the deduplicated list into `greenhouse_postings` / `other_postings`, filter only the former, then recombine (`other_postings + filtered_greenhouse`). This is implementation option (b) from the brief: LinkedIn/Indeed/Handshake mock postings, and Greenhouse-mock-fallback postings, are never passed through `filter_active_jobs` at all, since their URLs are fabricated and would otherwise be spuriously checked against live servers.
- Updated the existing test `test_search_and_store_filters_out_closed_job_urls` in `product/tests/test_job_service.py` to match this scoping: changed both mock job postings' `source` from `JobSource.LINKEDIN` to `JobSource.GREENHOUSE`, set `mock_scraper.data_source = "real"` explicitly (since a bare `MagicMock()`'s auto-attributes are truthy Mock objects, not the string `"real"`, and would otherwise silently fail the `== "real"` check), and changed the `search_and_store` call to search `[JobSource.GREENHOUSE]` instead of `[JobSource.LINKEDIN]`. The test's actual assertions (active URL kept, closed URL dropped, count == 1) are unchanged — only the setup was adjusted to trigger the now-narrower validation path.

### Finding 2 fix (eliminate live HTTP calls from the test suite)

`product/tests/test_job_service.py`:
- Added an `autouse=True` pytest fixture `mock_url_validation(request)` directly below the existing `temp_db` fixture. It inspects `request.node.name`: for every test except `test_search_and_store_filters_out_closed_job_urls`, it patches `resume_tailorer.job_search.job_service.URLValidator.check_url` to always return `"active"` for the duration of the test; for that one test, it yields immediately without patching, deferring entirely to that test's own local `mock.patch(...)` (which simulates per-URL active/closed responses and needs precedence over any file-wide default).
- Used the file's existing `from unittest import mock` import convention (not `from unittest.mock import patch`), consistent with how the rest of the file already calls `mock.patch(...)` and `mock.Mock()`.
- This fixture is defense-in-depth on top of the Finding 3 fix: after Finding 3, most of this file's existing tests no longer trigger `filter_active_jobs` at all (they use `LINKEDIN`/`INDEED` sources or mocks without `data_source == "real"`), but the fixture guards against any future test in this file that scrapes via a real-flagged Greenhouse mock and forgets to stub out network calls itself.

### Verification

- `cd product && time python -m pytest tests/ -q` → `176 passed in 61.95s` (wall clock `1m2.861s`), consistent with the pre-Task-3 baseline (~60-70s) and a clear regression fix from the ~160s observed with live HTTP calls in play.
- `cd product && python -m pytest tests/test_job_service.py -v` → all 14 tests pass in 0.40s, confirming this file in isolation makes no live network calls.
- Manually traced the caching fix per the brief's suggested verification (see Finding 1 section above): same-instance identity confirmed, `data_source` visibility across calls confirmed.
