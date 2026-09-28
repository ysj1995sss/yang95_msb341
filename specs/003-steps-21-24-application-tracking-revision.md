# Spec 003: Steps 21-24 application tracking revision

## Why

Steps 21-24 (application mode, submission recording, status tracking, dashboard) were already
substantially built, then audited against a stricter external brief. The audit found the existing
code is honest at the UI layer (decision 012's disclosure banner) but not yet safe at the code
layer: `SubmissionEngine._submit_to_platform()` performs a raw `requests.post()` against
`job.url` and treats any non-error HTTP response as a successful submission, setting
`ApplicationStatus.APPLIED` with no real confirmation evidence. Given decision 012 already proved
real ATS forms are JS-rendered SPAs with almost no server-side form fields, `job.url` is essentially
never a real form-submission endpoint — a real click of "Confirm & Submit" on Assist/Auto risks
silently recording a false "Applied" status. This is the single highest-priority fix.

Beyond that, the data model conflates "submission attempt" and "canonical application record,"
has no duplicate-submission protection, no job/profile snapshotting (unlike the pattern Steps
16-20 just established for `TailoringRun`), no status provenance/confidence, and a dashboard far
short of what Step 24 calls for.

## Scope

Extend and correct the existing `product/resume_tailorer/applications/` module. Do not rebuild.
Do not add a FastAPI layer for this (out of scope; `apps/api` has no application-tracking code
today and nothing in the audit calls for adding it). Do not attempt real browser automation —
decision 012's conclusion stands.

## Domain model changes

### `ATSCapability` (new)

Each ATS parser declares, instead of a bare `is_supported() -> bool`:

```
platform: str
manual_supported: bool = True
assist_supported: bool = False
auto_supported: bool = False
resume_upload: bool = False
profile_prefill: bool = False
custom_questions: bool = False
final_submission: bool = False
status_fetch: bool = False
notes: str = ""
```

Given decision 012's verified finding, Greenhouse/Lever/Ashby declare `assist_supported=False`,
`auto_supported=False`, `final_submission=False`, `profile_prefill=True` (prefill logic is real
and correct for whatever fields a page DOES expose — the gap is that pages expose almost none —
so this stays true to reflect what the code actually does when it can), `resume_upload=False`
(no code path ever attaches file bytes to a real POST), `custom_questions=False` (unimplemented).
Workday keeps `manual_supported=True` only, matching its existing `is_supported()=False`.

### Hard safety gate

`SubmissionEngine.apply_for_job` raises before any real POST if `mode != MANUAL`, `dry_run=False`,
and the platform's capability does not have `final_submission=True`. Since no platform currently
has it, this makes every non-manual real-submit attempt fail loudly and explain why, instead of
silently "succeeding" against a URL that was never a real submission endpoint. The Streamlit
"Confirm & Submit" button is disabled (not just checkbox-gated) whenever the selected mode's
platform lacks `final_submission`.

### `SubmissionAttempt` (new) vs `Application` (renamed/expanded from `ApplicationSubmission`)

Split the current single `applications` table concept in two:

- **`SubmissionAttempt`**: one row per attempt (including ones that fail before any record would
  previously have existed at all — e.g. the form fetch itself raising). Fields: `attempt_id`,
  `application_id`, `started_at`, `completed_at`, `mode`, `provider` (ats_platform), `result`
  (`SUBMISSION_STARTED` / `SUBMISSION_PENDING` / `SUBMITTED_CONFIRMED` / `SUBMISSION_FAILED` /
  `MANUALLY_CONFIRMED`), `error_code`, `error_message`, `confirmation_number`, `confirmation_url`.
- **`Application`**: the canonical record. Adds `job_snapshot` (JSON), `candidate_fit_snapshot`
  (JSON), `career_profile_version` (a hash, matching `profile_snapshot_hash`'s precedent from
  Steps 16-20), `answers_version`, alongside the existing `resume_used`/`ats_platform`/
  `form_url`/`form_fields_submitted`/`custom_answers`.

Backward compatibility: keep `ApplicationSubmission` as an alias/thin wrapper if practical rather
than breaking every existing caller and test in one pass; prefer additive columns over renames in
the SQLite schema, matching `apps/api/app/migrations.py`'s established additive-only pattern.

### Idempotency

Before creating a new `Application` for `(job_posting_id)` in a REAL (non-dry-run) submit, check
whether a `SubmissionAttempt` with `result=SUBMITTED_CONFIRMED` or `MANUALLY_CONFIRMED` already
exists for that job. If so, refuse (or require explicit override) rather than silently creating a
duplicate. Dry-run previews are exempt (they're not real submissions).

### Status tracking

Add `ASSESSMENT` and `UNKNOWN` to `ApplicationStatus`. Add `source` (`USER` / `EMAIL_INTEGRATION`
/ `ATS_INTEGRATION` / `SYSTEM`, default `USER`) and optional `confidence` / `evidence` to the
status-history row. No email/ATS integration exists — the fields exist so a future integration has
somewhere to write without a schema change, matching this repo's stated principle for Step 23's
"optional status automation." A user-entered status update is always allowed regardless of any
automated status already recorded (no silent revert).

### Dashboard (Step 24)

Expand `format_application_for_display` and the Streamlit page to show Company, Role, Applied
date, Mode, Candidate Fit, Resume version, Next action, Last update — sourced from the job
snapshot stored on the `Application` row (no new join needed against the live jobs table, since
the point is showing what was true AT SUBMISSION TIME). Add saved views (All/Saved/Applying/
Submitted/Assessments/Interviews/Offers/Rejected/Withdrawn) as status-group filters, plus filters
by company/role/mode/date and sorting. Add an application detail view showing everything the
"application detail view" section of the brief lists that this codebase actually has data for
(job snapshot, application URL, submitted resume path, candidate fit snapshot, form fields
submitted, confirmation, status history, notes, next action) — omit cover-letter/tailoring-report
fields the pipeline doesn't produce today rather than fabricating placeholders.

### Next action model

Add `next_action`, `next_action_due` (optional, user-entered only — never invented), `next_action_notes`
to `Application`, editable from the dashboard.

## Explicitly out of scope (unchanged from decision 012)

- Real browser automation for Assist/Auto.
- A documented ATS submission API investigation (still not explored).
- Multi-user/multi-tenant scoping (this module has no `user_id` today, matching
  `job_search/database.py`'s existing single-tenant local-Streamlit-tool pattern; out of scope to
  invent here).
- Email/ATS status integrations (architecture only, no implementation).
- Cover letter upload/tracking (no cover-letter generation exists anywhere in this product yet).

## Definition of done

Matches the brief's own Definition of Done section, scoped by the "explicitly out of scope" list
above. Both full test suites pass before and after. A decision record documents the build summary,
findings, and honest limitations, matching decisions 013/015's precedent.
