# Sprint 2 (Job Search Integration) — Final Whole-Branch Review Fix Report

All 5 Important + 5 Minor issues from the final review have been fixed in a single pass.

## Important Issues

### 1. `alternative_sources` never persisted — FIXED
- `product/resume_tailorer/job_search/database.py`
  - Added `alternative_sources TEXT` column to the `job_postings` table schema (`create_tables()`).
  - `save_job_posting()` now serializes `job.alternative_sources` to a JSON string and includes it in the `INSERT OR REPLACE` statement.
  - `_row_to_job_posting()` now deserializes the `alternative_sources` column back into a `List[str]` (defaults to `[]` if null/missing/corrupt).
- `product/resume_tailorer/pages/2_Job_Search.py`
  - In the job dashboard loop, added a caption under each job: `"Also posted on: <url1>, <url2>, ..."` shown only when `job.alternative_sources` is non-empty.

### 2. Fit Score never reaches the dashboard — FIXED
- `product/resume_tailorer/pages/2_Job_Search.py`
  - Added `CAREER_PROFILE_SESSION_KEY = "career_profile"` and, in `_render_job_dashboard()`, look up `st.session_state.get(CAREER_PROFILE_SESSION_KEY)`.
  - If a profile is present, calls `service.get_job_with_fit_score(job_id, career_profile)` per job (wrapped in try/except so a scoring failure never blocks the dashboard) and passes the resulting score into `format_job_for_display(job, fit_score)`.
  - If no profile is in session state, `fit_score` stays `None` and `format_job_for_display(job)` shows "N/A" as before — no crash, no blocking.
  - Added a `**Fit Score:**` line to the expander body so the score is actually visible.

### 3. UI made a false "no fabrication" claim — FIXED
- `product/resume_tailorer/pages/2_Job_Search.py`, `main()`
  - Replaced the misleading caption with a `st.warning(...)` "Demo Mode" disclosure stating the listings are simulated placeholder data, that real scraper integrations (LinkedIn, Indeed, Handshake, Greenhouse APIs) are a follow-up tracked in `decisions/`, and that real data will never be fabricated once live scraping ships.

### 4. Re-search silently reassigns user selections — FIXED
- `product/resume_tailorer/job_search/scrapers/{linkedin,indeed,handshake,greenhouse}_scraper.py`
  - Each mock scraper now imports `uuid` and appends `uuid.uuid4().hex[:8]` to every generated `source_id` (e.g. `f"linkedin_{i+1}_{uuid.uuid4().hex[:8]}"`), so repeated searches produce unique job IDs instead of colliding with previously-selected jobs via `INSERT OR REPLACE`.
  - Verified no test hardcodes the old fixed IDs from scraper output (only hand-constructed `JobPosting` fixtures use fixed IDs, which are unaffected).
- `product/resume_tailorer/pages/2_Job_Search.py`
  - Success message changed from `"Found and stored {count} new job posting(s)."` to `"Stored {count} job posting(s)."` to stop implying novelty/uniqueness.

### 5. Test pollutes real working directory — FIXED
- `product/tests/test_job_service.py`, `test_job_service_initialization_default_db`
  - Rewrote to assert the constructor's default via `inspect.signature(JobService.__init__).parameters["db_path"].default == "job_search.db"` (verifies intent without touching disk), then uses `monkeypatch.chdir(tmp_path)` before actually instantiating `JobService()` so any file the default path creates lands in a throwaway temp dir, never the real CWD.
- Deleted stray `job_search.db` files found at repo root (`./job_search.db`) and in `product/` (`./product/job_search.db`) left over from prior runs.
- `.gitignore`: added `*.db` (covers `job_search.db` and any other db files).

## Minor Issues

### 6. Unused `career_profile` parameter — FIXED
- `product/resume_tailorer/job_search/job_service.py`: removed `career_profile: Optional[CareerTruthProfile] = None` from `search_and_store()`'s signature and its docstring. Confirmed via grep that no caller (tests or UI) ever passed it.

### 7. `score_fit` returns `int` despite `-> float` annotation — FIXED
- `product/resume_tailorer/job_search/candidate_fit.py`, `score_fit()`: changed `return int(round(final_score))` to `return round(float(final_score), 1)`, so it now returns a genuine float (e.g. `85.0`, not `85`).
- Updated tests to match:
  - `product/tests/test_candidate_fit.py`: renamed `test_fit_score_is_integer` → `test_fit_score_is_float` and its assertion to `isinstance(score, float)`.
  - `product/tests/test_job_service.py`: `test_get_job_with_fit_score` assertion tightened from `isinstance(fit_score, (int, float))` to `isinstance(fit_score, float)`.

### 8. Hardcoded `current_year = 2024` — FIXED
- `product/resume_tailorer/job_search/candidate_fit.py`: added `from datetime import datetime` at the top and changed `current_year = 2024` to `current_year = datetime.now().year` in `_extract_years_from_dates()`.

### 9. `job_search.db` not gitignored — FIXED (same change as #5)
- `.gitignore` now includes `*.db`.

### 10. `pages/` directory location relative to `app.py` — VERIFIED, NOT A BUG
- Confirmed via `ls product/resume_tailorer/`: `app.py` and `pages/` are direct siblings inside `product/resume_tailorer/`, with `2_Job_Search.py` inside `pages/`. This is exactly the layout Streamlit auto-discovers for multi-page apps, so `app.py` needs no changes. No action taken.

## Test Verification

Ran from `product/`:
```
python -m pytest tests/ -v
```
Result: **156 passed** (0 failed), including all `test_job_service.py`, `test_candidate_fit.py`, `test_job_database.py`, `test_job_deduplicator.py`, `test_job_scrapers.py`, and `test_job_search_ui_helpers.py` suites.

`git status --short` after cleanup shows no untracked `.db` files.

## Files Changed
- `.gitignore`
- `product/resume_tailorer/job_search/candidate_fit.py`
- `product/resume_tailorer/job_search/database.py`
- `product/resume_tailorer/job_search/job_service.py`
- `product/resume_tailorer/job_search/scrapers/greenhouse_scraper.py`
- `product/resume_tailorer/job_search/scrapers/handshake_scraper.py`
- `product/resume_tailorer/job_search/scrapers/indeed_scraper.py`
- `product/resume_tailorer/job_search/scrapers/linkedin_scraper.py`
- `product/resume_tailorer/pages/2_Job_Search.py`
- `product/tests/test_candidate_fit.py`
- `product/tests/test_job_service.py`
- Deleted: `job_search.db`, `product/job_search.db` (stray artifacts from prior test runs)
