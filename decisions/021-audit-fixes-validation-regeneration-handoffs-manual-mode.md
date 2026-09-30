# 021: Audit fixes — trustworthy validation, immutable regeneration, connected workspaces, reliable Manual mode

**Date:** 2026-09-29
**Status:** Accepted

## Context

An external audit found that the test suites were green while real integration paths were
broken. The most serious findings:

- A blank PDF or a fabricated claim could be marked PASS.
- Regeneration could use the wrong resume.
- The five workspaces did not share the profile or the tailored resume.
- Manual mode depended on ATS form parsing.
- A preview created application records.

This decision covers audit tasks 1–4. Tasks 5–7 (multi-user deployment safety, the deferred
product capabilities, and engineering efficiency) are not addressed here.

## Decisions

### 1. Validation is authoritative

- **Blank or unreadable PDFs fail.** DOCX-path PDF technical issues (blank, unreadable,
  corrupt) become FAIL findings, using the same mapping as the freeform path
  (`findings_from_pdf_issues`).
- **Flagged claims block the resume until reviewed.** A freeform bullet flagged by the existing
  fabrication check (`check_bullet_pair_fabrication_risk`) is marked FAIL and left PENDING. The
  content gate raises `UNSUPPORTED_CLAIM_PRESENT` while that text is still in the resume.
- **An explicit accept downgrades the block to a warning.** It becomes
  `USER_CONFIRMED_UNVERIFIED_CLAIM`, so the resume is never shown as a clean PASS.
  - *Why:* changes are accepted one at a time (there is no bulk accept), and the detector also
    flags true rewording, such as "cloud" added to an AWS bullet. The user is the source of
    truth about their own facts; the system's job is to make sure nothing passes unreviewed.
  - *Rejected:* blocking even after acceptance. That would make true but differently worded
    claims impossible to use without editing the Fact Vault first.
- **Manual edits are validated against `manual_text`**, not the obsolete AI proposal.
- **One download rule.** A FAIL artifact is never returned in any response: the download
  endpoint, preview base64 fields, and regenerate base64 fields.

### 2. Regeneration is immutable

- **The exact resume is used.** API regeneration resolves the resume version stored on the run:
  the current upload if the version matches, otherwise the archived `ResumeFileVersion`. If that
  version is gone, the endpoint returns 409 instead of silently using a different resume.
- **"Keep original" restores removed bullets.** The bullet is reinserted under its own job,
  located through the profile, or appended at the end if the job can't be found.
- **Manual edits apply to every bullet**, including bullets the AI left unchanged.
- **The score comes from the final text.** Tailored alignment is recomputed from the
  regenerated text, in both the API and Streamlit. The Streamlit DOCX path's first run now does
  the same. `_score_resume` became a static method, since it never used the LLM.

### 3. The workspaces share one profile and one handoff

- **One career profile.** `session_profile.py` stores a `CareerTruthProfile` under
  `career_profile`. Fact Vault facts take precedence: a resume parsed in Tailoring Studio never
  overwrites them, and tailoring uses them when they are loaded.
- **Switching jobs resets tailoring.** `tailoring_session.py` tracks which job the studio is
  working on. A different job from Job Search replaces the description and discards the
  previous job's review and resume. The same job arriving again keeps the user's edits.
- **Launchpad receives the tailored resume.** After each run or regeneration that isn't a FAIL,
  Tailoring Studio writes the PDF to a file and hands Launchpad its path, SHA-256, version,
  validation status and match score. Launchpad uses the handoff only for the job it was made
  for, and a FAIL withdraws it.

### 4. Manual mode is reliable

- **Manual needs only a valid http(s) link.** It never fetches or parses the ATS page, so
  Workday, unknown platforms and unreachable pages can all be staged.
- **Preview never persists anything**, in any mode.
- **Staging is idempotent.** A job that already has a READY_TO_APPLY Manual application
  returns the existing record.
- **Preview approval is tied to what was previewed.** It is bound to a token covering the job
  ID, the resume file's SHA-256, the profile hash and the mode. Stage stays disabled after any
  of them changes.
- **Every real-submit failure is audited.** Each refusal or failure before a POST records a
  FAILED attempt with a code: `DUPLICATE_SUBMISSION`, `UNKNOWN_PLATFORM`,
  `UNSUPPORTED_PLATFORM`, `FORM_FETCH_FAILED`, `FORM_EMPTY` or `REQUIRED_FIELDS_UNFILLED`. The
  record has no status, so it never appears as an application.

## Verification

- Every finding has a regression test that reproduced it first.
- `tests/test_workspace_flow_e2e.py` drives the real Streamlit pages from Fact Vault through
  Job Search, Tailoring Studio and Apply Launchpad to the Tracker. The profile API and
  Greenhouse are stubbed. Streamlit's test runner cannot upload files, so the tailoring step is
  completed through the same validation and handoff functions the studio calls after a run.
- Product suite: 755 passed. API suite: 65 passed.

## Still open

- **Deployment safety (audit task 5):** Streamlit users share one SQLite database, and the API
  has a default JWT secret. The deployed app must not be promoted as multi-user.
- Freeform length gate and repair loop, the correction loop, custom application answers, and
  status sync.
- LLM timeouts, swallowed persistence errors, fit-score caching, and CI.

## Review after the first real-resume run (2026-09-30)

Run on a real DOCX resume, a live SoFi posting and the configured free model.

- **The truth gate held.** The model proposed adding "segmentation" to two bullets. The DOCX
  path rejected both because the word is not in the profile. The accepted edit, "SQL, Tableau",
  is in the verified skills list. The accept-downgrade rule (a user-accepted flagged claim
  becomes a warning) was not needed on the DOCX path; it applies to the freeform path only.
- **Keep the rule.** No evidence argues for making acceptance stricter.
- **Gap found:** the review screen's "Evidence" line for the accepted edit showed the bullet
  itself, not the skills-list entry that actually supports "SQL, Tableau". The claim is honest,
  but the explanation is misleading. Follow-up: show the real supporting fact.
- **Regeneration works as specified:** the rebuilt PDF stayed application-ready, and the match
  score was recomputed from the final text (100% before the rebuild, 92% after).
- **A dev-only hazard:** Streamlit's hot-reload can leave two copies of the same enum in a
  long-running dev server, which made Manual mode fail once after files changed. A clean server
  had no issue. It cannot happen on a normal deployment, where nothing reloads files.
