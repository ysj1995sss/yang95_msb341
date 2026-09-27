# Decision 012: Assist/Auto mode does not work against real ATS forms — scope down to Manual, be honest about it

**Date:** 2026-09-27
**Status:** Active

## Context

Steps 21-24 (application mode, submission recording, status tracking, dashboard) were already
substantially built: `ApplicationMode`/`ApplicationStatus` domain models, `ApplicationDatabase`
audit trail, `SubmissionEngine` with dry-run-by-default safety gates, ATS form parsers for
Greenhouse/Lever/Ashby, and a Streamlit Applications page with a submit tab and a status
dashboard. The existing disclosure banner already admitted the implementation was an untested MVP.

Before writing a spec to "finish" Steps 21-24, I live-tested the actual assumption the whole
Assist/Auto pipeline is built on: that fetching an ATS job-application URL with a plain HTTP GET
returns HTML containing real `<input name="...">`/`<select name="...">`/`<textarea name="...">`
elements, which `BaseATSParser._extract_fields()` (BeautifulSoup-based) can find and hand to
`FormFiller`.

Tested against a real, live Airbnb posting (the same one used in this session's Job Search smoke
test) at its real Greenhouse embed URL
(`job-boards.greenhouse.io/embed/job_app?token=...&for=airbnb`):

- The rendered page visually shows ~15+ fields: name, email, phone, country, location, resume
  upload, cover letter, LinkedIn, "how did you hear about this job," voluntary EEO questions,
  work authorization, sponsorship, privacy-policy acknowledgment, non-compete question, AI-usage
  attestation.
- The **raw HTML** behind that page has exactly **1 named `<input>`** (a checkbox) and
  **1 named `<textarea>`**, and **0 named `<select>`** elements — verified directly via
  `document.querySelectorAll('input[name]'), select[name]', 'textarea[name]')` in the live page.

Every other visible field is a client-side-rendered React component with no `name` attribute
present in server-delivered HTML. This is not a parser bug to fix — a static-HTML fetch-and-parse
approach structurally cannot see most of a real, modern Greenhouse application form. Lever and
Ashby are architecturally similar SPA-based platforms and are assumed to have the same problem,
though not independently verified.

## Decision

**Do not attempt to make Assist/Auto mode work against real ATS forms in this pass.** That would
require real browser automation (e.g. Playwright/Selenium: rendering JS, driving actual clicks/
fills, waiting for hydration) to even read the real fields, let alone fill and submit them. That
is a new, heavy dependency and a materially different risk category — a program literally
driving a browser to submit a real, live application to a real employer on the candidate's
behalf. That decision deserves its own explicit conversation with the product owner, not
something to build silently while "closing out" an existing spec item.

Instead, this pass:

1. **Wires the one real, safe gap in the existing flow**: "Apply" from the Job Search dashboard
   only ever handed off to the resume tailorer (`pending_tailor_job`), never to the Applications
   page — the job ID had to be copy-pasted by hand. Extended the same session-state handoff
   pattern to also carry the job ID forward.
2. **Makes the JS-rendered-form failure honest instead of cryptic.** The existing safety check
   (`SubmissionEngine.apply_for_job`, "refuse to submit an empty parsed form") already fails safe
   when zero fields are found — but surfaced only as a generic `ValueError`. The Applications page
   now recognizes this specific case and tells the user directly: this posting likely uses a
   JavaScript-rendered form Assist/Auto can't read; use Manual mode instead.
3. **Rewrites the disclosure banner** to state plainly, as verified fact rather than a hedge:
   Assist/Auto mode is unverified against real postings and Manual mode is the only mode
   currently recommended for actually applying — replacing "has not been tested against real
   Greenhouse/Lever/Ashby forms" (implying it might just need more testing) with what was
   actually found (it doesn't work against the one real form tested, and the reason is
   architectural, not a parsing edge case).

## Explicitly out of scope

- Playwright/Selenium-based real browser automation for Assist/Auto mode.
- Investigating whether Greenhouse, Lever, or Ashby expose a documented public submission API
  that could be used instead of driving the web UI (a real alternative worth investigating later,
  but not explored here).
- Verifying Lever/Ashby forms directly (assumed architecturally similar to Greenhouse based on
  being modern SPA-based ATS platforms, not independently tested).

## What would change our mind

If a documented, stable submission API exists for Greenhouse/Lever/Ashby (as opposed to scraping
their candidate-facing web UI), that would let Assist/Auto mode work without browser automation
or its risk profile — worth investigating before defaulting to Playwright. If the product
direction explicitly prioritizes auto-apply as a core differentiator, revisit this decision with
a dedicated spec for browser-automation-based submission, including its own safety model (how a
human stays in the loop before any real submission, given the field-visibility problem means the
system can no longer even show the user an accurate preview of everything that will be
submitted).
