# Handoff to Claude Code — Job Copilot

**Date:** 2026-09-25  
**From:** Cursor Cloud Agent (Steps 4–9 wrap-up)  
**Repo:** `ysj1995sss/yang95_msb341`  
**Audience:** A fresh Claude Code session continuing this product.

Read this file first, then `CLAUDE.md`, then the decisions listed below. Do not re-litigate Decisions 001 / 010 / 011 unless new evidence forces it.

---

## 1. What this product is

Automated job-application copilot for job seekers:

1. Upload resume → Career Truth Profile  
2. Search / discover jobs (Steps 3–9)  
3. Triage → **Apply** hands off into resume tailoring (Step 10+)  
4. Later: application modes, submission, status dashboard (Steps 21–24)

**Non-negotiable:** optimize presentation; never invent qualifications, employers, dates, or metrics.

---

## 2. Architecture (source of truth)

| Layer | Path | Role |
| --- | --- | --- |
| Product engine + Streamlit UI | `product/resume_tailorer/` | Primary implementation (Decision 001) |
| Job discovery engine | `product/resume_tailorer/job_search/` | Scout, dedupe, fit, quality, dashboard helpers, SQLite |
| Job Search UI | `product/resume_tailorer/pages/2_Job_Search.py` | Steps 4–9 UI |
| Tailor UI | `product/resume_tailorer/app.py` | Step 10+; consumes `pending_tailor_job` |
| FastAPI backend | `apps/api/` | Profile, jobs upsert/list, tailor; delegates dedupe/normalize/fit to product |
| Specs / decisions / sprints | `specs/`, `decisions/`, `sprints/` | Product truth and history |

Dual stack is intentional for now: Streamlit SQLite job search **and** API Job/UserJob. Shared logic lives in `product/`; API must not fork a second scorer or fingerprint.

---

## 3. Git / PR status (as of handoff)

| Item | Status |
| --- | --- |
| `main` | Includes PR #1 (first slice): fingerprint, normalize, cf-v2 fit, triage, APPLY → Step 10 |
| Branch `cursor/steps-4-9-dashboard-search-run-98e5` | PR **#2** — **DRAFT**, mergeable |
| PR #2 commit | `0168a68` — dashboard filters/sort, SearchRunSummary, job quality, API list parity, Decision 011 |
| Branch `cursor/steps-4-9-foundation-fit-triage-98e5` | Historical; already merged via PR #1 |

**Human must merge PR #2 (or instruct Claude to finish review + merge) before treating dashboard/search-run/quality as on `main`.**

PR: https://github.com/ysj1995sss/yang95_msb341/pull/2

---

## 4. What is already built (Do not rebuild)

### Sprint 1 — Resume tailoring (Steps 1–2, 10–20)
Working Streamlit tailor pipeline + PDF export + many real-world fidelity fixes. See `sprints/sprint-2-plan.md` history and decisions 002–004.

### Steps 4–9 — First slice (merged on `main` via PR #1) — Decision 010
- Shared `fingerprint.py` + `normalize.py`; API dedupe/normalize delegate here  
- `CandidateFitScorer` **cf-v2** (`score_fit_detailed` → `FitResult`) + competency map  
- Canonical triage: **SAVE / APPLY / PASS** (legacy interested/skipped/applied aliases)  
- APPLY → Step 10 via `PENDING_TAILOR_JOB_KEY` / `build_tailor_snapshot`  
- Greenhouse = live AVAILABLE; LinkedIn / Indeed / Handshake = LIMITED (demo)  
- Honest sponsorship: missing → `NOT_STATED` (never invent NO)

### Steps 4–9 — Completion slice (PR #2, not necessarily on `main` yet) — Decision 011
- `dashboard.py`: `DashboardFilters`, `filter_and_sort_jobs`, `filter_api_job_dicts`  
- `job_service.search_and_store` → **`SearchRunSummary`** (per-provider ok/failed/skipped; overall ok/partial/failed; `closed_filtered`)  
- `job_quality.py` / `api_quality.py`: active / stale / expired / broken / unknown  
- Streamlit Job Search: filters, sort, search-run summary UI  
- API `GET /jobs`: `min_fit`, `max_fit`, `min_salary`, `sponsorship`, `work_mode`, `source`, `quality`, `keyword`, `sort_by`, `sort_dir` + `quality_status` on items  

### Explicitly out of scope until product asks
- New live ATS (Lever/Ashby/Workday)  
- Persisted `search_runs` / RawJob tables  
- Live URL revalidation of every stored job on every dashboard load  
- Porting React `apps/web` or Chrome extension (noted in README as future)

---

## 5. Immediate next work (ordered)

### A. Land PR #2 (if still open)
1. Mark PR ready for review (or merge draft if owner prefers)  
2. Merge into `main`  
3. Locally: `git checkout main && git pull`

### B. End-to-end smoke (must pass before Sprint 3+)
From `product/` with venv active and `PYTHONPATH` including `product/`:

```bash
cd product
source .venv/bin/activate   # or create venv if missing
export PYTHONPATH="$(pwd)"
streamlit run resume_tailorer/app.py
```

Manual path:
1. Open **Job Search** page  
2. Goals: title + location required  
3. Prefer Greenhouse (live) or LIMITED sources for demo  
4. Run search → confirm **SearchRunSummary** (per-source ok/fail/partial)  
5. Use **Filters & sort** (fit, salary, sponsorship, quality, keyword, etc.)  
6. Mark **Apply** on a job → lands on Resume Tailorer with JD prefilled + fit banner  
7. Optionally tailor once to confirm Step 10 still works  

API smoke (optional):

```bash
cd apps/api
source .venv/bin/activate
export PYTHONPATH="/path/to/product:/path/to/apps/api"
# run uvicorn as project docs prescribe; exercise GET /jobs?... filters
```

Tests (regression gate):

```bash
cd product && source .venv/bin/activate
python -m pytest tests/ -k "job_search or job_service or job_quality or dashboard or fingerprint or candidate_fit or triage or url_validator or normalize or dedup" -q

cd ../apps/api && source .venv/bin/activate
PYTHONPATH=../../product:$(pwd) python -m pytest tests/test_jobs_fit.py tests/test_jobs_list_filters.py -q
```

### C. Then build Sprint 3+ (Steps 21–24)
Per `specs/job-copilot-workflow.html` / `specs/001-job-application-copilot.md`:

| Step | Title | Notes |
| --- | --- | --- |
| 21 | Choose Application Mode | Manual / Assist / Auto — scaffolding in `product/resume_tailorer/applications/` |
| 22 | Record Submission | Audit trail, resume version, scores |
| 23 | Update Application Status | Funnel statuses |
| 24 | Application Dashboard | Already partially exists as Streamlit page `3_Applications.py` — wire to real flow |

**Before coding Sprint 3+:** check for a spec under `specs/`. If none for application submission, **draft a spec and confirm with the builder** (per `CLAUDE.md`).

---

## 6. Key files to open first

```
CLAUDE.md
decisions/001-consolidate-product-architecture.md
decisions/010-steps-4-9-foundation-fit-triage.md
decisions/011-steps-4-9-dashboard-search-run-quality.md
specs/001-job-application-copilot.md
specs/job-copilot-workflow.html
product/resume_tailorer/job_search/job_service.py
product/resume_tailorer/job_search/candidate_fit.py
product/resume_tailorer/job_search/dashboard.py
product/resume_tailorer/pages/2_Job_Search.py
product/resume_tailorer/app.py
apps/api/app/jobs/list_router.py
product/resume_tailorer/applications/   # Sprint 3+ starting point
```

---

## 7. Environment setup checklist

1. Clone / pull repo from GitHub  
2. Python 3.12+ recommended  
3. `product/.venv` — install from product requirements / existing lock if present  
4. `apps/api/.venv` — install API deps (`pyproject.toml` / package metadata in `apps/api`)  
5. Always set `PYTHONPATH` to include `product/` when running Streamlit or API tests  
6. LLM keys: only for live tailor tests; never commit secrets or real PII (anonymize)  
7. Greenhouse live scrapes need network; LIMITED sources work offline with mocks  

---

## 8. Working agreements (mirror CLAUDE.md)

- Ask before large refactors or new dependencies  
- Spec first for non-trivial features (`specs/`)  
- Record meaningful choices in `decisions/`  
- Prefer shared helpers in `product/` over duplicating logic in `apps/api`  
- Preserve working APPLY → Step 10 handoff  
- Tests: pytest; do not claim done without running relevant suites  

---

## 9. Paste-ready first message for Claude Code

```text
Read HANDOFF-TO-CLAUDE-CODE.md and CLAUDE.md, then decisions 001, 010, and 011.

Current status:
- PR #1 merged on main (Steps 4–9 first slice).
- PR #2 may still be open (dashboard filters, SearchRunSummary, job quality, API list parity).

Your job:
1. Confirm whether PR #2 is merged; if not, help me land it, then pull main.
2. Run the smoke path: Job Search → filter/sort → Apply → Resume Tailorer handoff.
3. Run the job-search related pytest suites in product/ and apps/api.
4. After smoke passes, draft (or find) a spec for Sprint 3+ Steps 21–24, show me the plan, then implement application mode → submission recording → status → dashboard wiring. Reuse product/resume_tailorer/applications/ where possible.

Do not invent qualifications. Ask before large refactors or new deps. Prefer product/ as source of truth.
```

---

## 10. Known pitfalls

- **`search_and_store` returns `SearchRunSummary`**, not a raw `int` — use `.total_stored`  
- Streamlit must run with **`PYTHONPATH` pointing at `product/`** or imports of `resume_tailorer` fail  
- URL validation only for **real Greenhouse** results; mocks skip live HEAD checks  
- Closed URLs are filtered at ingest; quality labels apply to what remains  
- Sponsorship silence is **NOT_STATED**, not NO  
- Do not create a second Candidate Fit scorer in the API  

---

## 11. Success criteria for this handoff

- [ ] PR #2 on `main`  
- [ ] Smoke Apply → tailor works on latest `main`  
- [ ] Job-search pytest suites green  
- [ ] Spec + plan agreed for Steps 21–24  
- [ ] Steps 21–24 implemented, tested, and documented with a decision if architecture choices arise  
