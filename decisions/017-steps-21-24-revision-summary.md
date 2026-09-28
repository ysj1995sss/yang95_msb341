# Decision 017: Steps 21-24 application tracking revision — summary

**Date:** 2026-09-28
**Status:** Active

## Context

The user judged the previously-built Steps 21-24 (application mode, submission recording, status
tracking, dashboard) not good enough and supplied a stricter external improve-prompt with explicit
user-agency, compliance, and reliability requirements. Per that prompt's own instruction, an audit
ran first (see specs/003's "Why" section and the gap-analysis table given to the user before any
code changed). The audit found the existing code was honest at the UI layer (decision 012's
disclosure banner) but not safe at the code layer: `SubmissionEngine._submit_to_platform()` POSTed
to `job.url` and treated any non-error HTTP response as a successful real submission, which
decision 012 had already proven live is never a real form-submission endpoint for a modern
JS-rendered ATS. A real "Confirm & Submit" click risked silently recording a false "Applied"
status.

## Decision

Extended the existing module in six phases, each committed and tested independently, per
specs/003:

- **Phase B — the safety fix (decision 016):** Replaced the bare `is_supported() -> bool` with
  `ATSCapability` (manual/assist/auto_supported, resume_upload, profile_prefill,
  custom_questions, final_submission, status_fetch). Every platform declares
  `final_submission=False` today — none has been proven to work. `SubmissionEngine` hard-blocks
  the real POST on this flag as its last check before the network call; the Streamlit page
  disables "Confirm & Submit" proactively by looking up capability before rendering the button,
  not just via a checkbox the user could tick past.
- **Phase C — submission integrity:** Added `SubmissionAttempt` (a real-submit request now always
  leaves an audit row, including one blocked before any network call or one that fails after one),
  idempotency (`ApplicationDatabase.has_confirmed_submission()` refuses a second real submit for
  the same job instead of silently duplicating it), and immutable `job_snapshot`/
  `candidate_fit_snapshot`/`career_profile_version` captured at submission time — the same
  principle as `TailoringRun.profile_snapshot_json` from Steps 16-20. Schema changes are
  additive-only (`ALTER TABLE ADD COLUMN` guarded by an existence check), matching
  `apps/api/app/migrations.py`'s established pattern — a pre-existing local `applications.db`
  keeps working (verified by a dedicated migration test against a hand-built legacy-schema file).
- **Phase D — status provenance:** Added `source`/`confidence`/`evidence` to status history
  (default `USER`/`None`/`""`), exposed through `StatusTracker`, plus a `record_low_confidence_signal`
  entry point for a future email/ATS integration that doesn't exist yet — the fields exist so one
  could be added without a schema change, not because automation already works. A user's own
  status correction always overrides a prior automated entry regardless of its confidence.
- **Phase E — the dashboard (spec 003 Step 24):** Rebuilt `ui_helpers.py` with `STATUS_GROUPS`
  (saved views: All/Saved/Applying/Submitted/Assessments/Interviews/Offers/Rejected/Withdrawn),
  `filter_applications` (company/role/mode/min candidate fit, AND-combined), and
  `sort_applications` (newest/oldest/company/status/fit) — all pure, unit-tested functions. The
  Streamlit page now shows Company/Role/Applied date/Mode/Status/Candidate Fit/Resume version/
  Next action per row, an application detail section (job snapshot, application URL, resume used,
  fit at submission, fields submitted, confirmation, editable next-action), and status history
  with provenance shown for any non-USER entry. Live-verified in the browser against seeded real
  data (see "Live verification" below) — a real bug (the `min_fit` filter's "exclude unknown fit"
  logic silently failed to exclude anything when the threshold was exactly 0) was caught by its
  own unit test before it ever reached the browser.
- **Phase F — security pass:** Audited for sensitive-data logging (none found — no
  print/logging calls anywhere in the module) and credential storage (none — no ATS site
  passwords are ever stored). Added a parametrized regression test covering 20 sensitive/legally
  significant field-name patterns (work authorization, sponsorship, disability, veteran status,
  demographic questions, criminal history, salary expectations, relocation, legal attestations)
  confirming `FormFiller`'s alias whitelist never matches any of them. User-scoping (no `user_id`
  anywhere in this module) is unchanged and intentionally out of scope — this has always been a
  single-tenant-per-local-install tool matching `job_search/database.py`'s existing pattern, and
  there is no multi-user HTTP API surface for it to protect.
- **Phase G — acceptance:** A live, dry-run-only (never a real POST) run of the full
  `JobService.apply_for_job` → `SubmissionEngine` → `ApplicationDatabase` pipeline against a real,
  public Greenhouse listing succeeded, correctly parsed zero confidently-fillable fields (matching
  decision 012's finding that real Greenhouse pages expose almost no named form fields to a static
  fetch) without crashing, and correctly captured `job_snapshot`/`candidate_fit_snapshot` from real
  (unmocked) `JobPosting`/`CandidateFitScorer` objects.

## Live verification

- Full pytest suite: 685 product tests passing (started this session's work at 610, net +75
  across all six phases; 60 of those were pre-existing from before this revision).
- Streamlit dashboard live-tested in a real browser against two seeded, realistic applications
  (one Interview-status, one Rejected-status): saved views correctly filtered the table and
  updated the auto-selected application detail (verified switching from "All" → "Interviews" →
  "Rejected" each showed the correct single row and correct detail/status-history content); the
  empty-state message rendered correctly before any data existed.
- One live, safe (dry-run, no real POST) run of the full application pipeline against a real
  public Greenhouse job-listing URL — see Phase G above for the result.

## Known limitations, stated honestly

- **No ATS platform can complete a real submission yet.** This was true before this revision too
  (decision 012); what changed is that the code now says so honestly and refuses instead of
  silently pretending otherwise. Manual mode (get the link, apply yourself, track it here) remains
  the only reliable path to actually submitting an application.
- **Custom/job-specific question answering is still out of scope.** `custom_answers` is hardcoded
  to `{}`; nothing drafts or stores answers to free-text application questions. The architecture
  (spec 003's answer-source-of-truth model) anticipates this but it is not built.
- **`_submit_to_platform`'s success criterion (any non-error HTTP response) is unchanged and still
  weak** — it simply hasn't been reachable in production since no platform has `final_submission=True`.
  Before any platform's capability is ever flipped to `True`, this method itself should be
  revisited: a confirmation page/number check would be a stronger signal of a genuine successful
  submission than an HTTP status code alone.
- **No email/ATS status integration exists.** The `source`/`confidence`/`evidence` fields and
  `record_low_confidence_signal` are groundwork only.
- **Still no `user_id`/multi-tenancy** in this module, matching the pre-existing pattern elsewhere
  in the Streamlit product. Would need to be added if this module were ever exposed through
  `apps/api` to real multiple concurrent users.
- **Real ATS submission architecturally requires browser automation** to even read a real form's
  fields (decision 012's finding, unchanged) — still explicitly out of scope pending its own
  product conversation about that risk profile.

## What would change our mind

If a documented, stable submission API is found for Greenhouse/Lever/Ashby, or real browser
automation is explicitly approved under its own risk-acceptance decision, flip that platform's
`ATSCapability.final_submission` to `True` and revisit `_submit_to_platform`'s success check at the
same time — the capability model and safety gate built here are the template; the retry/idempotency/
attempt-tracking machinery around them does not need to change.
